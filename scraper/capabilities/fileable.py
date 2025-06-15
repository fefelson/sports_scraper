from abc import ABC, abstractmethod
from typing import Any, List, Optional
import json 
import os
import pickle


#################################################################
#################################################################

def get_file_agent(fileType: Optional[str]=None) -> "FileAgent":
    default = "pickle"
    if not fileType:
        fileType = default
    return {"pickle": PickleAgent, "json": JSONAgent}[fileType]


#################################################################
#################################################################


class Fileable(ABC):
    """Handles loading and saving data to/from files."""


    def __init__(self):
        self.fileAgent = None
        self.filePath = None
    

    def file_exists(self) -> bool:
        return os.path.exists(self.filePath)
    

    @abstractmethod
    def set_file_path(self, filePath: str=None):
        raise NotImplementedError


    def set_file_agent(self, fileAgent: "FileAgent"):
        self.fileAgent = fileAgent


    def read_file(self) -> Any:
        return self.fileAgent.read(self.filePath)


    def write_file(self, fileableObj: Any) -> None:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.filePath), exist_ok=True)
        self.fileAgent.write(self.filePath, fileableObj)


###################################################################
###################################################################


class FileAgent(ABC):

    @abstractmethod
    def get_ext() -> str:
        raise NotImplementedError
    

    @abstractmethod
    def read(filePath: str) -> Any:
        raise NotImplementedError
    

    @abstractmethod
    def write(filePath: str, fileObject: Any):
        raise NotImplementedError


###################################################################
###################################################################


class JSONAgent(FileAgent):
    _ext="json"

    @staticmethod
    def get_ext() -> str:
        return JSONAgent._ext
    

    @staticmethod
    def read(filePath: str) -> dict:
        with open(filePath, "r") as fileIn:
            return json.load(fileIn)
        

    @staticmethod
    def write(filePath: str, fileObj: dict):
        with open(filePath, "w") as file:
           json.dump(fileObj, file,  indent=4)


###################################################################
###################################################################


class PickleAgent(FileAgent):
    _ext = "pkl"

    @staticmethod
    def get_ext() -> str:
        return PickleAgent._ext
    

    @staticmethod
    def read(filePath: str) -> Any:
        with open(filePath, "rb") as file:
            return pickle.load(file)
        

    @staticmethod
    def write(filePath: str, fileObj: Any) -> None:
        with open(filePath, "wb") as file:
            pickle.dump(fileObj, file)


#######################################################################
#######################################################################

