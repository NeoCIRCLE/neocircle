from ..models import method_cache

class TestClass(object):
    id = None
    called = 0

    def __init__(self, id):
        self.id = id

    @method_cache()
    def method(self, s):
        # print 'Called TestClass(%d).method(%s)' % (self.id, s)
        self.called += 1
        return self.id + len(s)
