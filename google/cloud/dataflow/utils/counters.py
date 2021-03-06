# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# cython: profile=False
# cython: overflowcheck=True

"""Counters collect the progress of the Worker for reporting to the service."""

import threading


class Counter(object):
  """A counter aggregates a series of values.

  The aggregation kind of the Counter is specified when the Counter
  is created.  The values aggregated must be of an appropriate for the
  aggregation used.  Aggregations supported are listed in the code.

  (The aggregated value will be reported to the Dataflow service.)

  Do not create directly; call CounterFactory.get_counter instead.

  Attributes:
    name: the name of the counter, a string
    aggregation_kind: one of the aggregation kinds defined by this class.
    total: the total size of all the items passed to update()
    elements: the number of times update() was called
  """

  # Aggregation kinds.  The protocol uses string names, so the values
  # assigned here are not externally visible.

  # Numeric:
  SUM = 1
  MAX = 2
  MIN = 3
  MEAN = 4  # arithmetic mean

  # Boolean
  AND = 5
  OR = 6

  _KIND_NAME_MAP = {SUM: 'SUM', MAX: 'MAX', MIN: 'MIN',
                    MEAN: 'MEAN', AND: 'AND', OR: 'OR'}

  def aggregation_kind_str(self):
    return self._KIND_NAME_MAP.get(self.aggregation_kind,
                                   'kind%d' % self.aggregation_kind)

  def __init__(self, name, aggregation_kind):
    """Creates a Counter object.

    Args:
      name: the name of this counter.  Typically has three parts:
        "step-output-counter".
      aggregation_kind: one of the kinds defined by this class.
    """
    self.name = name
    self.aggregation_kind = aggregation_kind
    # optimized update doesn't handle all types
    assert aggregation_kind == self.SUM or aggregation_kind == self.MEAN
    self.c_total = 0
    self.py_total = 0
    self.elements = 0

  def update(self, count):
    try:
      self._update_small(count)
    except OverflowError:
      self.py_total += count
    self.elements += 1

  def _update_small(self, delta):
    new_total = self.c_total + delta  # overflow is checked
    self.c_total = new_total

  @property
  def total(self):
    return self.c_total + self.py_total

  def value(self):
    if self.aggregation_kind == self.SUM:
      return self.total
    elif self.aggregation_kind == self.MEAN:
      return float(self.total)/self.elements
    else:
      # This can't happen, because we check in __init__
      raise TypeError('%s.value(): unsupported aggregation_kind' % self)

  def __str__(self):
    return '<%s>' % self._str_internal()

  def __repr__(self):
    return '<%s at %s>' % (self._str_internal(), hex(id(self)))

  def _str_internal(self):
    return '%s %s %s/%s' % (self.name, self.aggregation_kind_str(),
                            self.total, self.elements)


class AggregatorCounter(Counter):
  """A Counter that represents a step-specific instance of an Aggregator.

  Do not create directly; call CounterFactory.get_aggregator_counter instead.
  """


class Accumulator(Counter):
  """An internal Counter that sums.

  Because this class is used only internally (not reported to the
  Dataflow service), its name is not important.  It is not necessary
  to supply a name when creating one.
  """

  def __init__(self, name='unnamed'):
    """Creates an Accumulator object.

    Args:
      name: a suggested name-part.  Optional.
    """
    super(Accumulator, self).__init__('internal-%s-%x' % (name, id(self)),
                                      Counter.SUM)


# Counters that represent Accumulators have names starting with this
USER_COUNTER_PREFIX = 'user-'


class CounterFactory(object):
  """Keeps track of unique counters."""

  def __init__(self):
    self.counters = {}

    # Lock to be acquired when accessing the counters map.
    self._lock = threading.Lock()

  def get_counter(self, name, aggregation_kind):
    """Returns a counter with the requested name.

    Passing in the same name will return the same counter; the
    aggregation_kind must agree.

    Args:
      name: the name of this counter.  Typically has three parts:
        "step-output-counter".
      aggregation_kind: one of the kinds defined by this class.
    Returns:
      A new or existing counter with the requested name.
    """
    with self._lock:
      counter = self.counters.get(name, None)
      if counter:
        assert counter.aggregation_kind == aggregation_kind
      else:
        counter = Counter(name, aggregation_kind)
        self.counters[name] = counter
      return counter

  def get_aggregator_counter(self, step_name, aggregator):
    """Returns an AggregationCounter for this step's aggregator.

    Passing in the same values will return the same counter.

    Args:
      step_name: the name of this step.
      aggregator: an Aggregator object.
    Returns:
      A new or existing counter.
    """
    with self._lock:
      name = '%s%s-%s' % (USER_COUNTER_PREFIX, step_name, aggregator.name)
      aggregation_kind = aggregator.aggregation_kind
      counter = self.counters.get(name, None)
      if counter:
        assert isinstance(counter, AggregatorCounter)
        assert counter.aggregation_kind == aggregation_kind
      else:
        counter = AggregatorCounter(name, aggregation_kind)
        self.counters[name] = counter
      return counter

  def get_counters(self):
    """Returns the current set of counters.

    Returns:
      An iterable that contains the current set of counters. To make sure that
      multiple threads can iterate over the set of counters, we return a new
      iterable here. Note that the actual set of counters may get modified after
      this method returns hence the returned iterable may be stale.
    """
    with self._lock:
      return self.counters.values()

  def get_aggregator_values(self, aggregator_or_name):
    """Returns dict of step names to values of the aggregator."""
    with self._lock:
      return get_aggregator_values(
          aggregator_or_name, self.counters, lambda counter: counter.value())


def get_aggregator_values(aggregator_or_name, counter_dict,
                          value_extractor=None):
  """Extracts the named aggregator value from a set of counters.

  Args:
    aggregator_or_name: an Aggregator object or the name of one.
    counter_dict: a dict object of {name: value_wrapper}
    value_extractor: a function to convert the value_wrapper into a value.
      If None, no extraction is done and the value is return unchanged.

  Returns:
    dict of step names to values of the aggregator.
  """
  name = aggregator_or_name
  if value_extractor is None:
    value_extractor = lambda x: x
  if not isinstance(aggregator_or_name, basestring):
    name = aggregator_or_name.name
    return {n: value_extractor(c) for n, c in counter_dict.iteritems()
            if n.startswith(USER_COUNTER_PREFIX)
            and n.endswith('-%s' % name)}
