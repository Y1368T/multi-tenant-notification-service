from .base import BaseModel
from .tenant import *
from .sms import *
from .in_app import *
from .email import *
#new
from .whatsapp import *
#new
from .providers_supported import ProviderModel
from .user import *
from .message_aggregate import MessageAggregateModel

__all__ = ["BaseModel", "ProviderModel", "MessageAggregateModel"]
__all__.extend(tenant.__all__)
__all__.extend(sms.__all__)
__all__.extend(in_app.__all__)
__all__.extend(email.__all__)
__all__.extend(user.__all__)
#new
__all__.extend(whatsapp.__all__)
#new