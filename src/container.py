import logging

from nameko.containers import ServiceContainer as NamekoServiceContainer


logger = logging.getLogger(__name__)


class ServiceContainer(NamekoServiceContainer):

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
