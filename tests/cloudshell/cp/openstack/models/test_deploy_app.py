from cloudshell.cp.core.request_actions import DeployVMRequestActions

from cloudshell.cp.openstack.models import OSNovaImgDeployApp


def test_deploy_app(deploy_app_request_factory, cs_api):
    app_name = "app name"
    image_id = "image id"
    instance_flavor = "instance flavor"
    add_floating_ip = True
    floating_ip_subnet_id = "floating ip subnet id"
    auto_udev = True
    user = "user"
    password = "password"
    public_ip = "public ip"
    action_id = "action id"
    request = deploy_app_request_factory(
        app_name,
        image_id,
        instance_flavor,
        add_floating_ip,
        floating_ip_subnet_id,
        auto_udev,
        user,
        password,
        public_ip,
        action_id,
    )

    DeployVMRequestActions.register_deployment_path(OSNovaImgDeployApp)
    request_actions = DeployVMRequestActions.from_request(request, cs_api)
    app: OSNovaImgDeployApp = request_actions.deploy_app  # noqa

    assert app.app_name == app_name.replace(" ", "-")
    assert app.image_id == image_id
    assert app.instance_flavor == instance_flavor
    assert app.add_floating_ip == add_floating_ip
    assert app.floating_ip_subnet_id == floating_ip_subnet_id
    assert app.auto_udev == auto_udev
    assert app.user == user
    assert app.password == password
    assert app.public_ip == public_ip
    assert app.actionId == action_id
