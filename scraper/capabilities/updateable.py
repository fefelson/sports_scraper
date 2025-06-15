from abc import ABC, abstractmethod


################################################################################
################################################################################


class Updateable(ABC):


    @abstractmethod
    def needs_update(self):
        raise NotImplementedError


    @abstractmethod
    def update(self):
        raise NotImplementedError