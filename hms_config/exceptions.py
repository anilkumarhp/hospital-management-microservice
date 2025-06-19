from rest_framework.views import exception_handler
from rest_framework.response import Response

def custom_exception_handler(exc, context):
    # First, get the standard error response from DRF
    response = exception_handler(exc, context)

    # If an error response was generated, then customize it
    if response is not None:
        # ★-- THE FIX IS HERE --★
        # Check if the standard response data is a dictionary.
        # If it is, we can extract the detail. If not (e.g., it's a list for a 
        # validation error), we just use the whole data as the message.
        if isinstance(response.data, dict):
            message = response.data.get('detail', str(exc))
        else:
            message = response.data

        custom_response_data = {
            'status': 'error',
            'error': {
                'code': response.status_code,
                'message': message
            }
        }
        response.data = custom_response_data
    
    return response