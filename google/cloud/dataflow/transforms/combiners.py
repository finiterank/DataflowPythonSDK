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

"""A library of basic combiner PTransform subclasses."""

from __future__ import absolute_import

import heapq
import itertools
import random

from google.cloud.dataflow.transforms import core
from google.cloud.dataflow.transforms import ptransform
from google.cloud.dataflow.typehints import Any
from google.cloud.dataflow.typehints import Dict
from google.cloud.dataflow.typehints import KV
from google.cloud.dataflow.typehints import List
from google.cloud.dataflow.typehints import Tuple
from google.cloud.dataflow.typehints import TypeVariable
from google.cloud.dataflow.typehints import Union
from google.cloud.dataflow.typehints import with_input_types
from google.cloud.dataflow.typehints import with_output_types


__all__ = [
    'Count',
    'Mean',
    'Sample',
    'Top',
    'ToDict',
    'ToList',
    ]


class Mean(object):
  """Combiners for computing arithmetic means of elements."""

  class Globally(ptransform.PTransform):
    """combiners.Mean.Globally computes the arithmetic mean of the elements."""

    def apply(self, pcoll):
      return pcoll | core.CombineGlobally(MeanCombineFn())

  class PerKey(ptransform.PTransform):
    """combiners.Mean.PerKey finds the means of the values for each key."""

    def apply(self, pcoll):
      return pcoll | core.CombinePerKey(MeanCombineFn())


# TODO(laolu): This type signature is overly restrictive. This should be
# more general.
@with_input_types(Union[float, int, long])
@with_output_types(float)
class MeanCombineFn(core.CombineFn):
  """CombineFn for computing an arithmetic mean."""

  def create_accumulator(self):
    return (0, 0)

  def add_input(self, (sum_, count), element):
    return sum_ + element, count + 1

  def merge_accumulators(self, accumulators):
    sums, counts = zip(*accumulators)
    return sum(sums), sum(counts)

  def extract_output(self, (sum_, count)):
    if count == 0:
      return float('NaN')
    return sum_ / float(count)


class Count(object):
  """Combiners for counting elements."""

  class Globally(ptransform.PTransform):
    """combiners.Count.Globally counts the total number of elements."""

    def apply(self, pcoll):
      return pcoll | core.CombineGlobally(CountCombineFn())

  class PerKey(ptransform.PTransform):
    """combiners.Count.PerKey counts how many elements each unique key has."""

    def apply(self, pcoll):
      return pcoll | core.CombinePerKey(CountCombineFn())

  class PerElement(ptransform.PTransform):
    """combiners.Count.PerElement counts how many times each element occurs."""

    def apply(self, pcoll):
      paired_with_void_type = KV[pcoll.element_type, Any]
      return (pcoll
              | (core.Map('%s:PairWithVoid' % self.label, lambda x: (x, None))
                 .with_output_types(paired_with_void_type))
              | core.CombinePerKey(CountCombineFn()))


@with_input_types(Any)
@with_output_types(int)
class CountCombineFn(core.CombineFn):
  """CombineFn for computing PCollection size."""

  def create_accumulator(self):
    return 0

  def add_inputs(self, accumulator, elements):
    return accumulator + len(elements)

  def merge_accumulators(self, accumulators):
    return sum(accumulators)

  def extract_output(self, accumulator):
    return accumulator


class Top(object):
  """Combiners for obtaining extremal elements."""
  # pylint: disable=no-self-argument

  @ptransform.ptransform_fn
  def Of(label, pcoll, n, compare, *args, **kwargs):
    """Obtain a list of the compare-most N elements in a PCollection.

    This transform will retrieve the n greatest elements in the PCollection
    to which it is applied, where "greatest" is determined by the comparator
    function supplied as the compare argument.

    compare should be an implementation of "a < b" taking at least two arguments
    (a and b). Additional arguments and side inputs specified in the apply call
    become additional arguments to the comparator.

    Args:
      label: display label for transform processes.
      pcoll: PCollection to process.
      n: number of elements to extract from pcoll.
      compare: as described above.
      *args: as described above.
      **kwargs: as described above.
    """
    return pcoll | core.CombineGlobally(
        label, TopCombineFn(n, compare), *args, **kwargs)

  @ptransform.ptransform_fn
  def PerKey(label, pcoll, n, compare, *args, **kwargs):
    """Identifies the compare-most N elements associated with each key.

    This transform will produce a PCollection mapping unique keys in the input
    PCollection to the n greatest elements with which they are associated, where
    "greatest" is determined by the comparator function supplied as the compare
    argument.

    compare should be an implementation of "a < b" taking at least two arguments
    (a and b). Additional arguments and side inputs specified in the apply call
    become additional arguments to the comparator.

    Args:
      label: display label for transform processes.
      pcoll: PCollection to process.
      n: number of elements to extract from pcoll.
      compare: as described above.
      *args: as described above.
      **kwargs: as described above.

    Raises:
      TypeCheckError: If the output type of the input PCollection is not
        compatible with KV[A, B].
    """
    return pcoll | core.CombinePerKey(
        label, TopCombineFn(n, compare), *args, **kwargs)

  @ptransform.ptransform_fn
  def Largest(label, pcoll, n):
    """Obtain a list of the greatest N elements in a PCollection."""
    return pcoll | Top.Of(label, n, lambda a, b: a < b)

  @ptransform.ptransform_fn
  def Smallest(label, pcoll, n):
    """Obtain a list of the least N elements in a PCollection."""
    return pcoll | Top.Of(label, n, lambda a, b: b < a)

  @ptransform.ptransform_fn
  def LargestPerKey(label, pcoll, n):
    """Identifies the N greatest elements associated with each key."""
    return pcoll | Top.PerKey(label, n, lambda a, b: a < b)

  @ptransform.ptransform_fn
  def SmallestPerKey(label, pcoll, n):
    """Identifies the N least elements associated with each key."""
    return pcoll | Top.PerKey(label, n, lambda a, b: b < a)


T = TypeVariable('T')
@with_input_types(T)
@with_output_types(List[T])
class TopCombineFn(core.CombineFn):
  """CombineFn doing the combining for all of the Top transforms.

  The comparator function supplied as an argument to the apply call invoking
  TopCombineFn should be an implementation of "a < b" taking at least two
  arguments (a and b). Additional arguments and side inputs specified in the
  apply call become additional arguments to the comparator.
  """

  # Actually pickling the comparison operators (including, often, their
  # entire globals) can be very expensive.  Instead refer to them by index
  # in this dictionary, which is populated on construction (including
  # unpickling).
  compare_by_id = {}

  def __init__(self, n, compare, _compare_id=None):  # pylint: disable=invalid-name
    self._n = n
    self._compare = compare
    self._compare_id = _compare_id or id(compare)
    TopCombineFn.compare_by_id[self._compare_id] = self._compare

  def __reduce_ex__(self, _):
    return TopCombineFn, (self._n, self._compare, self._compare_id)

  class _HeapItem(object):
    """A wrapper for values supporting arbitrary comparisons.

    The heap implementation supplied by Python is a min heap that always uses
    the __lt__ operator if one is available. This wrapper overloads __lt__,
    letting us specify arbitrary precedence for elements in the PCollection.
    """

    def __init__(self, item, compare_id, *args, **kwargs):
      # item:         wrapped item.
      # compare:      an implementation of the pairwise < operator.
      # args, kwargs: extra arguments supplied to the compare function.
      self.item = item
      self.compare_id = compare_id
      self.args = args
      self.kwargs = kwargs

    def __lt__(self, other):
      return TopCombineFn.compare_by_id[self.compare_id](
          self.item, other.item, *self.args, **self.kwargs)

  def create_accumulator(self, *args, **kwargs):
    return []  # Empty heap.

  def add_input(self, heap, element, *args, **kwargs):
    # Note that because heap is a min heap, heappushpop will discard incoming
    # elements that are lesser (according to compare) than those in the heap
    # (since that's what you would get if you pushed a small element on and
    # popped the smallest element off). So, filtering a collection with a
    # min-heap gives you the largest elements in the collection.
    item = self._HeapItem(element, self._compare_id, *args, **kwargs)
    if len(heap) < self._n:
      heapq.heappush(heap, item)
    else:
      heapq.heappushpop(heap, item)
    return heap

  def merge_accumulators(self, heaps, *args, **kwargs):
    heap = []
    for e in itertools.chain(*heaps):
      if len(heap) < self._n:
        heapq.heappush(heap, e)
      else:
        heapq.heappushpop(heap, e)
    return heap

  def extract_output(self, heap, *args, **kwargs):
    # Items in the heap are heap-ordered. We put them in sorted order, but we
    # have to use the reverse order because the result is expected to go
    # from greatest to least (as defined by the supplied comparison function).
    return [e.item for e in sorted(heap, reverse=True)]


# Python's pickling is broken for nested classes.
_HeapItem = TopCombineFn._HeapItem  # pylint: disable=protected-access


class Largest(TopCombineFn):

  def __init__(self, n):
    super(Largest, self).__init__(n, lambda a, b: a < b)

  def default_label(self):
    return 'Largest(%s)' % self._n


class Smallest(TopCombineFn):

  def __init__(self, n):
    super(Smallest, self).__init__(n, lambda a, b: b < a)

  def default_label(self):
    return 'Smallest(%s)' % self._n


class Sample(object):
  """Combiners for sampling n elements without replacement."""
  # pylint: disable=no-self-argument

  @ptransform.ptransform_fn
  def FixedSizeGlobally(label, pcoll, n):
    return pcoll | core.CombineGlobally(label, SampleCombineFn(n))

  @ptransform.ptransform_fn
  def FixedSizePerKey(label, pcoll, n):
    return pcoll | core.CombinePerKey(label, SampleCombineFn(n))


T = TypeVariable('T')
@with_input_types(T)
@with_output_types(List[T])
class SampleCombineFn(core.CombineFn):
  """CombineFn for all Sample transforms."""

  def __init__(self, n):
    super(SampleCombineFn, self).__init__()
    # Most of this combiner's work is done by a TopCombineFn. We could just
    # subclass TopCombineFn to make this class, but since sampling is not
    # really a kind of Top operation, we use a TopCombineFn instance as a
    # helper instead.
    self._top_combiner = TopCombineFn(n, lambda a, b: a < b)

  def create_accumulator(self):
    return self._top_combiner.create_accumulator()

  def add_input(self, heap, element):
    # Before passing elements to the Top combiner, we pair them with random
    # numbers. The elements with the n largest random number "keys" will be
    # selected for the output.
    return self._top_combiner.add_input(heap, (random.random(), element))

  def merge_accumulators(self, heaps):
    return self._top_combiner.merge_accumulators(heaps)

  def extract_output(self, heap):
    # Here we strip off the random number keys we added in add_input.
    return [e for _, e in self._top_combiner.extract_output(heap)]


class _TupleCombineFnBase(core.CombineFn):

  def __init__(self, *combiners):
    self._combiners = [core.CombineFn.maybe_from_callable(c) for c in combiners]

  def create_accumulator(self):
    return [c.create_accumulator() for c in self._combiners]

  def merge_accumulators(self, accumulators):
    return [c.merge_accumulators(a)
            for c, a in zip(self._combiners, zip(*accumulators))]

  def extract_output(self, accumulator):
    return tuple([c.extract_output(a)
                  for c, a in zip(self._combiners, accumulator)])


class TupleCombineFn(_TupleCombineFnBase):

  def add_inputs(self, accumulator, elements):
    return [c.add_inputs(a, e)
            for c, a, e in zip(self._combiners, accumulator, zip(*elements))]

  def with_common_input(self):
    return SingleInputTupleCombineFn(*self._combiners)


class SingleInputTupleCombineFn(_TupleCombineFnBase):

  def add_inputs(self, accumulator, elements):
    return [c.add_inputs(a, elements)
            for c, a in zip(self._combiners, accumulator)]


class ToList(ptransform.PTransform):
  """A global CombineFn that condenses a PCollection into a single list."""

  def __init__(self, label='ToList'):
    super(ToList, self).__init__(label)

  def apply(self, pcoll):
    return pcoll | core.CombineGlobally(self.label, ToListCombineFn())


T = TypeVariable('T')
@with_input_types(T)
@with_output_types(List[T])
class ToListCombineFn(core.CombineFn):
  """CombineFn for to_list."""

  def create_accumulator(self):
    return []

  def add_input(self, accumulator, element):
    accumulator.append(element)
    return accumulator

  def merge_accumulators(self, accumulators):
    return sum(accumulators, [])

  def extract_output(self, accumulator):
    return accumulator


class ToDict(ptransform.PTransform):
  """A global CombineFn that condenses a PCollection into a single dict.

  PCollections should consist of 2-tuples, notionally (key, value) pairs.
  If multiple values are associated with the same key, only one of the values
  will be present in the resulting dict.
  """

  def __init__(self, label='ToDict'):
    super(ToDict, self).__init__(label)

  def apply(self, pcoll):
    return pcoll | core.CombineGlobally(self.label, ToDictCombineFn())


K = TypeVariable('K')
V = TypeVariable('V')
@with_input_types(Tuple[K, V])
@with_output_types(Dict[K, V])
class ToDictCombineFn(core.CombineFn):
  """CombineFn for to_dict."""

  def create_accumulator(self):
    return dict()

  def add_input(self, accumulator, element):
    key, value = element
    accumulator[key] = value
    return accumulator

  def merge_accumulators(self, accumulators):
    result = dict()
    for a in accumulators:
      result.update(a)
    return result

  def extract_output(self, accumulator):
    return accumulator


def curry_combine_fn(fn, args, kwargs):
  if not args and not kwargs:
    return fn

  else:

    class CurriedFn(core.CombineFn):
      """CombineFn that applies extra arguments."""

      def create_accumulator(self):
        return fn.create_accumulator(*args, **kwargs)

      def add_input(self, accumulator, element):
        return fn.add_input(accumulator, element, *args, **kwargs)

      def add_inputs(self, accumulator, elements):
        return fn.add_inputs(accumulator, elements, *args, **kwargs)

      def merge_accumulators(self, accumulators):
        return fn.merge_accumulators(accumulators, *args, **kwargs)

      def extract_output(self, accumulator):
        return fn.extract_output(accumulator, *args, **kwargs)

      def apply(self, elements):
        return fn.apply(elements, *args, **kwargs)

    return CurriedFn()


class PhasedCombineFnExecutor(object):
  """Executor for phases of combine operations."""

  def __init__(self, phase, fn, args, kwargs):

    self.combine_fn = curry_combine_fn(fn, args, kwargs)

    if phase == 'all':
      self.apply = self.full_combine
    elif phase == 'add':
      self.apply = self.add_only
    elif phase == 'merge':
      self.apply = self.merge_only
    elif phase == 'extract':
      self.apply = self.extract_only
    else:
      raise ValueError('Unexpected phase: %s' % phase)

  def full_combine(self, elements):  # pylint: disable=invalid-name
    return self.combine_fn.apply(elements)

  def add_only(self, elements):  # pylint: disable=invalid-name
    return self.combine_fn.add_inputs(
        self.combine_fn.create_accumulator(), elements)

  def merge_only(self, accumulators):  # pylint: disable=invalid-name
    return self.combine_fn.merge_accumulators(accumulators)

  def extract_only(self, accumulator):  # pylint: disable=invalid-name
    return self.combine_fn.extract_output(accumulator)
