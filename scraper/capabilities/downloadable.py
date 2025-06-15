from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


#################################################################
#################################################################


class Downloadable(ABC):
    """Enables downloading data from a URL"""


    @abstractmethod
    def download(self) -> Dict[str, Any]:
        """Fetches data from the URL and converts it into dict."""
        raise NotImplementedError



#################################################################
#################################################################


class DownloadAgent(ABC):
    
    @abstractmethod
    def _fetch_url(url: str):
        pass

    @abstractmethod
    def fetch_boxscore(url: str):
        pass 

    @abstractmethod
    def fetch_scoreboard(url: str):
        pass
    


    

   