from __future__ import annotations

from contextlib import suppress
from logging import Logger
from typing import TYPE_CHECKING, ClassVar, Generator

import attr
from glanceclient import exc as glance_exc
from glanceclient.v2.client import Client as GlanceClient

from cloudshell.cp.openstack.exceptions import ImageNotFound

if TYPE_CHECKING:
    from cloudshell.cp.openstack.os_api.api import OsApi


@attr.s(auto_attribs=True, str=False)
class Image:
    api: ClassVar[OsApi]
    _glance: ClassVar[GlanceClient]
    _logger: ClassVar[Logger]

    id: str  # noqa: A003
    name: str

    def __str__(self) -> str:
        return f"Image '{self.name}'"

    @classmethod
    def from_dict(cls, image_dict: dict) -> Image:
        return cls(image_dict["id"], image_dict["name"])

    @classmethod
    def get(cls, id_: str) -> Image:
        cls._logger.debug(f"Getting an image with ID '{id_}'")
        try:
            image_dict = cls._glance.images.get(id_)
        except glance_exc.HTTPNotFound:
            raise ImageNotFound(id_)
        return cls.from_dict(image_dict)

    @classmethod  # noqa: A003
    def all(cls) -> Generator[Image, None, None]:  # noqa: A003
        cls._logger.debug("Get all images")
        for image_dict in cls._glance.images.list():
            yield cls.from_dict(image_dict)

    def remove(self) -> None:
        with suppress(glance_exc.HTTPNotFound):
            self._glance.images.delete(self.id)
