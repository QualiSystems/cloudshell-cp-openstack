from __future__ import annotations

import pytest
from glanceclient import exc as glance_exc

from cloudshell.cp.openstack.exceptions import ImageNotFound


@pytest.fixture
def image(os_api_v2):
    return os_api_v2.Image.from_dict({"id": "id", "name": "name"})


def test_get_image(os_api_v2, glance):
    image_id = "image id"

    image = os_api_v2.Image.get(image_id)

    glance.images.get.assert_called_once_with(image_id)
    image_dict = glance.images.get()
    assert image.id == image_dict["id"]
    assert image.name == image_dict["name"]
    assert str(image) == f"Image '{image_dict['name']}'"


def test_image_not_found(os_api_v2, glance):
    glance.images.get.side_effect = glance_exc.HTTPNotFound

    with pytest.raises(ImageNotFound):
        os_api_v2.Image.get("id")


def test_remove_image(image, glance):
    image.remove()

    glance.images.delete.assert_called_once_with(image.id)


def test_get_all_images(os_api_v2, glance):
    id1 = "id1"
    id2 = "id2"
    name1 = "name1"
    name2 = "name2"
    glance.images.list.return_value = [
        {"id": id1, "name": name1},
        {"id": id2, "name": name2},
    ]

    images = list(os_api_v2.Image.all())

    assert len(images) == 2
    image1, image2 = images

    assert image1.id == id1
    assert image1.name == name1

    assert image2.id == id2
    assert image2.name == name2
