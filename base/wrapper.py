from abc import ABC, abstractmethod

__all__ = ("WrapperBase",)


class WrapperBase(ABC):
    @abstractmethod
    def serialise(self) -> dict:
        raise NotImplementedError

    @classmethod
    def parse(cls, data: dict):
        """Classmethod to create an instance of the wrapper class from dict representation of data

        Args:
            data (dict): Dictionary representation of class data

        Returns:
            Type[WrapperBase]: Wrapper class instance that inherits from WrapperBase
        """
        return cls(data)
