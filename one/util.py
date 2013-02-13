def keygen(length=1024):
    import os, base64
    from datetime import date
    from Crypto.PublicKey import RSA

    key = RSA.generate(length, os.urandom)
    try:
        pub = key.exportKey('OpenSSH')
        if not pub.startswith("ssh-"):
            raise ValueError(pub)
    except:
        ssh_rsa = '00000007' + base64.b16encode('ssh-rsa')
        exponent = '%x' % (key.e, )
        if len(exponent) % 2:
            exponent = '0' + exponent

        ssh_rsa += '%08x' % (len(exponent) / 2, )
        ssh_rsa += exponent

        modulus = '%x' % (key.n, )
        if len(modulus) % 2:
            modulus = '0' + modulus

        if modulus[0] in '89abcdef':
            modulus = '00' + modulus

        ssh_rsa += '%08x' % (len(modulus) / 2, )
        ssh_rsa += modulus

        pub = 'ssh-rsa %s' % (
            base64.b64encode(base64.b16decode(ssh_rsa.upper())), )
    return key.exportKey(), "%s %s" % (pub, "cloud-%s" % date.today())
