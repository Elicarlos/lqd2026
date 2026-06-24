from cryptography.fernet import Fernet

masterkey = "'jpvBrLzACz-NHI12Z5Yo7UTOC90fSLLM0Lp84SW_Pmw='"


def tokenGen(code):
    f = Fernet(masterkey)
    return f.encrypt(code)
