# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""DirectPipelineRunner, executing on the local machine.

The DirectPipelineRunner class implements what is called in Dataflow
parlance the "direct runner". Such a runner executes the entire graph
of transformations belonging to a pipeline on the local machine.
"""

from __future__ import absolute_import

import collections
import itertools
import logging

from google.cloud.dataflow import coders
from google.cloud.dataflow import error
from google.cloud.dataflow.pvalue import EmptySideInput
from google.cloud.dataflow.pvalue import IterablePCollectionView
from google.cloud.dataflow.pvalue import ListPCollectionView
from google.cloud.dataflow.pvalue import SingletonPCollectionView
from google.cloud.dataflow.runners.common import DoFnRunner
from google.cloud.dataflow.runners.common import DoFnState
from google.cloud.dataflow.runners.runner import PipelineResult
from google.cloud.dataflow.runners.runner import PipelineRunner
from google.cloud.dataflow.runners.runner import PipelineState
from google.cloud.dataflow.runners.runner import PValueCache
from google.cloud.dataflow.transforms import DoFnProcessContext
from google.cloud.dataflow.transforms.window import GlobalWindows
from google.cloud.dataflow.transforms.window import WindowedValue
from google.cloud.dataflow.typehints.typecheck import OutputCheckWrapperDoFn
from google.cloud.dataflow.typehints.typecheck import TypeCheckError
from google.cloud.dataflow.typehints.typecheck import TypeCheckWrapperDoFn
from google.cloud.dataflow.utils import counters
from google.cloud.dataflow.utils.options import TypeOptions


class DirectPipelineRunner(PipelineRunner):
  """A local pipeline runner.

  The runner computes everything locally and does not make any attempt to
  optimize for time or space.
  """

  def __init__(self, cache=None):
    # Cache of values computed while the runner executes a pipeline.
    self._cache = cache if cache is not None else PValueCache()
    self._counter_factory = counters.CounterFactory()
    # Element counts used for debugging footprint issues in the direct runner.
    # The values computed are used only for logging and do not take part in
    # any decision making logic. The key for the counter dictionary is either
    # the full label for the transform producing the elements or a tuple
    # (full label, output tag) for ParDo transforms since they can output values
    # on multiple outputs.
    self.debug_counters = {}
    self.debug_counters['element_counts'] = collections.Counter()

  def get_pvalue(self, pvalue):
    """Gets the PValue's computed value from the runner's cache."""
    try:
      return self._cache.get_pvalue(pvalue)
    except KeyError:
      raise error.PValueError('PValue is not computed.')

  def clear_pvalue(self, pvalue):
    """Removes a PValue from the runner's cache."""
    self._cache.clear_pvalue(pvalue)

  def skip_if_cached(func):  # pylint: disable=no-self-argument
    """Decorator to skip execution of a transform if value is cached."""

    def func_wrapper(self, pvalue, *args, **kwargs):
      logging.debug('Current: Debug counters: %s', self.debug_counters)
      if self._cache.is_cached(pvalue):  # pylint: disable=protected-access
        return
      else:
        func(self, pvalue, *args, **kwargs)
    return func_wrapper

  def run(self, pipeline, node=None):
    super(DirectPipelineRunner, self).run(pipeline, node)
    logging.info('Final: Debug counters: %s', self.debug_counters)
    return DirectPipelineResult(state=PipelineState.DONE,
                                counter_factory=self._counter_factory)

  @skip_if_cached
  def run_CreatePCollectionView(self, transform_node):
    transform = transform_node.transform
    view = transform.view
    values = self._cache.get_pvalue(transform_node.inputs[0])
    if isinstance(view, SingletonPCollectionView):
      has_default, default_value = view._view_options()  # pylint: disable=protected-access
      if len(values) == 0:  # pylint: disable=g-explicit-length-test
        if has_default:
          result = default_value
        else:
          result = EmptySideInput()
      elif len(values) == 1:
        # TODO(ccy): Figure out whether side inputs should ever be given as
        # windowed values
        result = values[0].value
      else:
        raise ValueError(("PCollection with more than one element accessed as "
                          "a singleton view: %s.") % view)
    elif isinstance(view, IterablePCollectionView):
      result = [v.value for v in values]
    elif isinstance(view, ListPCollectionView):
      result = [v.value for v in values]
    else:
      raise NotImplementedError

    self._cache.cache_output(transform_node, result)

  @skip_if_cached
  def run_ParDo(self, transform_node):
    transform = transform_node.transform
    # TODO(gildea): what is the appropriate object to attach the state to?
    context = DoFnProcessContext(label=transform.label,
                                 state=DoFnState(self._counter_factory))

    side_inputs = [self._cache.get_pvalue(view)
                   for view in transform_node.side_inputs]

    # TODO(robertwb): Do this type checking inside DoFnRunner to get it on
    # remote workers as well?
    options = transform_node.inputs[0].pipeline.options
    if options is not None and options.view_as(TypeOptions).runtime_type_check:
      transform.dofn = TypeCheckWrapperDoFn(
          transform.dofn, transform.get_type_hints())

    # TODO(robertwb): Should this be conditionally done on the workers as well?
    transform.dofn = OutputCheckWrapperDoFn(
        transform.dofn, transform_node.full_label)

    class RecordingReceiverSet(object):
      def __init__(self, tag):
        self.tag = tag
      def output(self, element):
        results[self.tag].append(element)

    class TaggedReceivers(dict):
      def __missing__(self, key):
        return RecordingReceiverSet(key)

    results = collections.defaultdict(list)
    # Some tags may be empty.
    for tag in transform.side_output_tags:
      results[tag] = []

    runner = DoFnRunner(transform.dofn, transform.args, transform.kwargs,
                        side_inputs, transform_node.inputs[0].windowing,
                        context, TaggedReceivers(),
                        step_name=transform_node.full_label)
    runner.start()
    for v in self._cache.get_pvalue(transform_node.inputs[0]):
      runner.process(v)
    runner.finish()

    self._cache.cache_output(transform_node, [])
    for tag, value in results.items():
      self.debug_counters['element_counts'][
          (transform_node.full_label, tag)] += len(value)
      self._cache.cache_output(transform_node, tag, value)

  @skip_if_cached
  def run_GroupByKeyOnly(self, transform_node):
    result_dict = collections.defaultdict(list)
    # The input type of a GroupByKey will be KV[Any, Any] or more specific.
    kv_type_hint = transform_node.transform.get_type_hints().input_types[0]
    key_coder = coders.registry.get_coder(kv_type_hint[0].tuple_types[0])

    for wv in self._cache.get_pvalue(transform_node.inputs[0]):
      if (isinstance(wv, WindowedValue) and
          isinstance(wv.value, collections.Iterable) and len(wv.value) == 2):
        k, v = wv.value
        # We use as key a string encoding of the key object to support keys
        # that are based on custom classes. This mimics also the remote
        # execution behavior where key objects are encoded before being written
        # to the shuffler system responsible for grouping.
        result_dict[key_coder.encode(k)].append(v)
      else:
        raise TypeCheckError('Input to GroupByKeyOnly must be a PCollection of '
                             'windowed key-value pairs. Instead received: %r.'
                             % wv)

    gbk_result = map(
        GlobalWindows.WindowedValue,
        ((key_coder.decode(k), v) for k, v in result_dict.iteritems()))
    self.debug_counters['element_counts'][
        transform_node.full_label] += len(gbk_result)
    self._cache.cache_output(transform_node, gbk_result)

  @skip_if_cached
  def run_Create(self, transform_node):
    transform = transform_node.transform
    create_result = [GlobalWindows.WindowedValue(v) for v in transform.value]
    self.debug_counters['element_counts'][
        transform_node.full_label] += len(create_result)
    self._cache.cache_output(transform_node, create_result)

  @skip_if_cached
  def run_Flatten(self, transform_node):
    flatten_result = list(
        itertools.chain.from_iterable(
            self._cache.get_pvalue(pc) for pc in transform_node.inputs))
    self.debug_counters['element_counts'][
        transform_node.full_label] += len(flatten_result)
    self._cache.cache_output(transform_node, flatten_result)

  @skip_if_cached
  def run_Read(self, transform_node):
    # TODO(chamikara) Implement a more generic way for passing PipelineOptions
    # to sources and sinks when using DirectRunner.
    source = transform_node.transform.source
    source.pipeline_options = transform_node.inputs[0].pipeline.options
    with source.reader() as reader:
      read_result = [GlobalWindows.WindowedValue(e) for e in reader]
      self.debug_counters['element_counts'][
          transform_node.full_label] += len(read_result)
      self._cache.cache_output(transform_node, read_result)

  @skip_if_cached
  def run__NativeWrite(self, transform_node):
    sink = transform_node.transform.sink
    sink.pipeline_options = transform_node.inputs[0].pipeline.options
    with sink.writer() as writer:
      for v in self._cache.get_pvalue(transform_node.inputs[0]):
        self.debug_counters['element_counts'][transform_node.full_label] += 1
        writer.Write(v.value)


class DirectPipelineResult(PipelineResult):
  """A DirectPipelineResult provides access to info about a pipeline."""

  def __init__(self, state, counter_factory=None):
    super(DirectPipelineResult, self).__init__(state)
    self._counter_factory = counter_factory

  def aggregated_values(self, aggregator_or_name):
    return self._counter_factory.get_aggregator_values(aggregator_or_name)
