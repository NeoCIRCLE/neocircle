from mock import patch


class MockCeleryMixin(object):
    def _pre_setup(self):
        self.reloadtask_patcher = patch(
            'firewall.tasks.local_tasks.reloadtask.apply_async', spec=True)
        self.reloadtask_patcher.start()

        self.kombu_patcher = patch('kombu.connection.Connection.ensure',
                                   side_effect=RuntimeError())
        self.kombu_patcher.start()

        self.check_queue_patcher = patch('vm.tasks.vm_tasks.check_queue',
                                         return_value=True)
        self.check_queue_patcher.start()

        super(MockCeleryMixin, self)._pre_setup()

    def _post_teardown(self):
        self.reloadtask_patcher.stop()
        self.kombu_patcher.stop()

        super(MockCeleryMixin, self)._post_teardown()
