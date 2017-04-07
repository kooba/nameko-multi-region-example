import logging

from nameko.containers import ServiceContainer as NamekoServiceContainer


logger = logging.getLogger(__name__)


class ServiceContainer(NamekoServiceContainer):
    """Custom implementation of Nameko's ServiceContainer

    Right before Nameko starts our container, we will remove any entrypoints
    which have been listed in `ENTRYPOINT_BLACKLIST` section of the service's
    config file.

    To enable custom ServiceContainer implementation we have to tell Nameko
    about its location by setting `SERVICE_CONTAINER_CLS` config value
    to the location of this class:
    `SERVICE_CONTAINER_CLS: src.container.ServiceContainer`
    """

    def start(self):
        blacklist = self.config.get('ENTRYPOINT_BLACKLIST') or ()

        for entrypoint in list(self.entrypoints):
            if entrypoint.method_name in blacklist:
                self.entrypoints.remove(entrypoint)
                logger.info(
                    'Removing blacklisted entrypoint: %s',
                    entrypoint.method_name
                )

        super(ServiceContainer, self).start()
