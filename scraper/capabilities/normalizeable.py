from abc import ABC, abstractmethod
from typing import Any, Optional


##################################################################
##################################################################



class Normalizable(ABC):
    """Handles normalizg web data."""
    

    @abstractmethod
    def normalize(self, webData: dict) -> Any:
        raise NotImplementedError


######################################################################
######################################################################


class NormalAgent(ABC):
    
    @abstractmethod
    def normalize_scoreboard(self, webData: dict) -> dict:
        raise NotImplementedError


    @abstractmethod
    def normalize_boxscore(self, webData: dict) -> dict:
        raise NotImplementedError


    @abstractmethod
    def normalize_player(self, webData: dict) -> dict:
        raise NotImplementedError