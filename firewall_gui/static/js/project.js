angular.module('firewall', []).config(
['$routeProvider', function($routeProvider) {
    $routeProvider.when('/rules/', {
        templateUrl: '/static/partials/rule-list.html',
        controller: RuleListCtrl
    }).
    otherwise({
        redirectTo: '/rules/'
    });
}]);

function RuleListCtrl($scope, $http) {
    $http.get('/firewall/rules/').success(function success(data) {
        $scope.rules = data;
    });
}
