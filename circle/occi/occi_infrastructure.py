""" Implementation of the OCCI - Infrastructure extension classes """


from occi_core import Resource


class Compute(Resource):
    """ OCCI 1.2 - Infrastructure extension - Compute """
    def __init__(self, vm):
        """ Creates a Compute instance of a VM instance object """
        self.location = "/compute/%d" % (vm.pk)
        self.vm = vm
