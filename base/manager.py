import json
import logging
import os
from abc import ABC, abstractmethod

from aiofile import async_open

from .wrapper import WrapperBase, WrapperBaseType

__all__ = ("ManagerBase",)


class ManagerBase(ABC):
    def __init__(self, _dir: str, name: str):
        self.__dir = _dir
        self.file_path = f"{self.__dir}/{name}.json"
        self._logger = logging.getLogger()
        self.__wrapper_data: dict = {}

    @abstractmethod
    async def load(self) -> None:
        pass

    async def _load(self, *, name: str):
        """Initialiser, will create necessary directories. Must be overridden

        Args:
            name (str): The name of the manager
        """
        if not os.path.exists(self.__dir):
            os.mkdir(self.__dir)

        await self.get_or_create_wrapper()
        self._logger.info(f"[{name}] Successfully loaded")

    async def __get_wrapper_data(self) -> dict:
        """Get wrapper data from disk and initialise in-memory object

        Raises:
            FileNotFoundError: Wrapper data file was not found on disk

        Returns:
            dict: Wrapper data dict
        """
        if not self.__wrapper_data:
            async with async_open(self.file_path, "r") as afile:
                data = json.loads(await afile.read())
                self.__wrapper_data = data
        return self.__wrapper_data

    async def write(self, wrapper: WrapperBase) -> None:
        """Writes wrapper data to disk and updates in-memory object

        Args:
            wrapper (WrapperBase): The wrapper object to serialise
        """
        data = wrapper.serialise()
        self.__wrapper_data = data
        async with async_open(self.file_path, "w") as afile:
            await afile.write(json.dumps(data, indent=4))

    @abstractmethod
    async def get_or_create_wrapper(self) -> WrapperBase:
        pass

    async def _get_or_create_wrapper(
        self, *, cls: type[WrapperBaseType]
    ) -> WrapperBaseType:
        """Get wrapper from data, or create datafile if it doesn't exist. Must be overridden

        Args:
            cls (type[WrapperBaseType]): Class that inherits from WrapperBase

        Returns:
            WrapperBaseType: An instantiated wrapper of the provided class
        """
        try:
            data = await self.__get_wrapper_data()
        except FileNotFoundError:
            data = {}
            async with async_open(self.file_path, "w") as afile:
                await afile.write(str(data))
        return cls.parse(data)
