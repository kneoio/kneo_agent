import logging.config
import re

class ServerInfoFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record, 'getMessage'):
            msg = record.getMessage()
            record.msg = re.sub(r'^[^ ]* [^ ]* [^ ]* [^ ]* python\[\d+\]: ', '', msg)
        return True

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'clean': {
            'format': '%(asctime)s - %(levelname)s - %(message)s'
        }
    },
    'filters': {
        'server_filter': {
            '()': ServerInfoFilter,
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'clean',
            'filters': ['server_filter']
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console']
    }
}

def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)