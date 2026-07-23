from enum import StrEnum, auto

class MediaType(StrEnum):
    "The class contains all types of media"
    MOVIE = auto()      
    TV_SERIES = auto()  
    BOOK = auto()       

class Status(StrEnum):
    "The class contains all types of status"
    WATCHED = auto()    
    WATCHING = auto()   
    PLANNED = auto()    
    ON_HOLD = auto()    

class Genre(StrEnum):
    "The class contains all types of genres"
    pass