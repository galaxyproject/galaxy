import re
from dataclasses import dataclass
from typing import (
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    Tuple,
    TypeVar,
)

from .auto_identifiers import filename_to_element_identifier


class HasName(Protocol):
    name: str


T = TypeVar("T", bound=HasName)

# matches pairing.ts in the client
COMMON_FILTERS: Dict[str, Tuple[str, str]] = {
    "illumina": ("_1", "_2"),
    "Rs": ("_R1", "_R2"),
    "dot12s": (".1.fastq", ".2.fastq"),
}


def paired_element_list_identifier(forward: str, reverse: str) -> Optional[str]:
    for forward_filter, reverse_filter in COMMON_FILTERS.values():
        if forward_filter in forward and reverse_filter in reverse:
            forward_base = filename_to_element_identifier(re.sub(f"{forward_filter}", "", forward))
            reverse_base = filename_to_element_identifier(re.sub(f"{reverse_filter}", "", reverse))
            common_base = longest_prefix(forward_base, reverse_base)
            return common_base

    forward_base = filename_to_element_identifier(forward)
    reverse_base = filename_to_element_identifier(reverse)
    common_base = longest_prefix(forward_base, reverse_base)
    return common_base


def longest_prefix(str1: str, str2: str) -> str:
    prefix = ""
    min_len = min(len(str1), len(str2))
    for i in range(min_len):
        if str1[i] == str2[i]:
            prefix += str1[i]
        else:
            break
    return prefix


@dataclass
class Pair(Generic[T]):
    name: str
    forward: T
    reverse: T


@dataclass
class PartialPair(Generic[T]):
    name: str
    forward: Optional[T]
    reverse: Optional[T]

    def to_pair(self) -> Pair[T]:
        assert self.forward
        assert self.reverse
        return Pair(name=self.name, forward=self.forward, reverse=self.reverse)


@dataclass
class AutoPairResponse(Generic[T]):
    paired: List[Pair[T]]
    unpaired: List[T]


def auto_pair(elements: List[T]) -> AutoPairResponse[T]:
    filter_type = guess_initial_filter_type(elements)
    if filter_type:
        forward_filter, reverse_filter = COMMON_FILTERS[filter_type]
        forward_elements, reverse_elements = split_elements_by_filter(elements, forward_filter, reverse_filter)
        partial_pairs: Dict[str, PartialPair[T]] = {}
        for forward_element in forward_elements:
            forward_base = filename_to_element_identifier(re.sub(f"{forward_filter}", "", forward_element.name))

            if forward_base not in partial_pairs:
                partial_pairs[forward_base] = PartialPair(name=forward_base, forward=forward_element, reverse=None)
        for reverse_element in reverse_elements:
            reverse_base = filename_to_element_identifier(re.sub(f"{reverse_filter}", "", reverse_element.name))
            if reverse_base not in partial_pairs:
                partial_pairs[reverse_base] = PartialPair(name=reverse_base, forward=None, reverse=reverse_element)
            else:
                partial_pairs[reverse_base].reverse = reverse_element

        unpaired: List[T] = elements.copy()
        for forward_element in forward_elements:
            unpaired.remove(forward_element)
        for reverse_element in reverse_elements:
            unpaired.remove(reverse_element)

        full_pairs: List[Pair[T]] = []
        for partial_pair in partial_pairs.values():
            if partial_pair.forward is None:
                assert partial_pair.reverse
                unpaired.append(partial_pair.reverse)
            elif partial_pair.reverse is None:
                assert partial_pair.forward
                unpaired.append(partial_pair.forward)
            else:
                full_pairs.append(partial_pair.to_pair())
        return AutoPairResponse(paired=full_pairs, unpaired=unpaired)
    else:
        return AutoPairResponse(paired=[], unpaired=elements)


def guess_initial_filter_type(elements: List[T]) -> Optional[str]:
    illumina = 0
    dot12s = 0
    Rs = 0

    # Iterate through elements and count occurrences of filter patterns
    for element in elements:
        if ".1.fastq" in element.name or ".2.fastq" in element.name:
            dot12s += 1
        elif "_R1" in element.name or "_R2" in element.name:
            Rs += 1
        elif "_1" in element.name or "_2" in element.name:
            illumina += 1

    # Determine the most likely filter type
    if illumina == 0 and dot12s == 0 and Rs == 0:
        return None
    elif illumina > dot12s and illumina > Rs:
        return "illumina"
    elif dot12s > illumina and dot12s > Rs:
        return "dot12s"
    elif Rs > illumina and Rs > dot12s:
        return "Rs"
    else:
        return "illumina"


def split_elements_by_filter(elements: List[T], forward_filter: str, reverse_filter: str) -> Tuple[List[T], List[T]]:
    filters = [re.compile(forward_filter), re.compile(reverse_filter)]
    split: Tuple[List[T], List[T]] = ([], [])
    for element in elements:
        for i, filter in enumerate(filters):
            if element.name and filter.search(element.name):
                split[i].append(element)
    return split
