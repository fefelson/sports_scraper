from abc import ABC, abstractmethod
from typing import Any, Optional


####################################################################
####################################################################



class Processable(ABC):


    @abstractmethod
    def process(self, data: Any) -> Optional[Any]:
        pass

    