import logging

from nameko.containers import ServiceContainer as NamekoServiceContainer


logger = logging.getLogger(__name__)


def validate_entrypoint_blacklist(blacklist, entrypoints):
    all_names = {ept.method_name for ept in entrypoints}
    trimmed_blacklist = {ep for ep in blacklist if ep}
    invalid_blacklist = trimmed_blacklist - all_names
    if invalid_blacklist:
        logger.warn(
            'Invalid entrypoint-blacklist entries: %s',
            sorted(invalid_blacklist)
        )


class ServiceContainer(NamekoServiceContainer):

    @property
    def entrypoint_blacklist(self):
        return self.config.get('ENTRYPOINT_BLACKLIST') or ()

    def start(self):
        blacklist = self.entrypoint_blacklist
        validate_entrypoint_blacklist(blacklist, self.entrypoints)

        for entrypoint in list(self.entrypoints):
            if entrypoint.method_name in blacklist:
                self.entrypoints.remove(entrypoint)
                logger.info(
                    'Removing blacklisted entrypoint: %s',
                    entrypoint.method_name
                )

        super(ServiceContainer, self).start()
