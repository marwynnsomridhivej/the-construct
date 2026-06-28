from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, TypeVar

__all__ = (
    "WrapperBase",
    "WrapperBaseType",
)

if TYPE_CHECKING:
    WrapperBaseType = TypeVar("WrapperBaseType", bound="WrapperBase")


class WrapperBase(ABC):
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def serialise(self) -> dict:
        raise NotImplementedError

    @classmethod
    def parse(cls: type[WrapperBaseType], data: dict) -> WrapperBaseType:
        """Classmethod to create an instance of the wrapper class from dict representation of data

        Args:
            cls (type[WrapperBaseType]): The wrapper class instance
            data (dict): Dictionary representation of class data

        Returns:
            WrapperBaseType: Wrapper class instance that inherits from WrapperBase
        """
        return cls(data)
