from abc import (
    ABC,
    abstractmethod,
)

from ._schema import (
    TourDetails,
    TourList,
)


class ToursRegistry(ABC):
    @abstractmethod
    def get_tours(self) -> TourList:
        """Return list of tours."""

    @abstractmethod
    def tour_contents(self, tour_id: str) -> TourDetails:
        """Return tour contents."""

    @abstractmethod
    def load_tour(self, tour_id: str) -> TourDetails:
        """Reload tour and return its contents."""
