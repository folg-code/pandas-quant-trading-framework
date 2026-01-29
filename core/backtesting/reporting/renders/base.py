from abc import ABC, abstractmethod


class BaseRenderer(ABC):

    @abstractmethod
    def render(self, report_data: dict):
        pass
