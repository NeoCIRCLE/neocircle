var module = angular.module('firewall', []).config(
['$routeProvider', function($routeProvider) {
    $routeProvider.when('/rules/', {
        templateUrl: '/static/partials/rule-list.html',
        controller: ListController('/firewall/rules/')
    }).when('/hosts/', {
        templateUrl: '/static/partials/host-list.html',
        controller: ListController('/firewall/hosts/')
    }).
    otherwise({
        redirectTo: '/rules/'
    });
}]);

function range(a, b) {
    var res = [];
    do res.push(a++);
    while (a < b)
    return res;
}

function matchAnything(obj, query) {
    var expr = new RegExp(query, 'i')
    for(var i in obj) {
        var prop = obj[i];
        if(typeof prop === 'number' && prop == query) return true;
        if(typeof prop === 'string' && prop.match(expr)) return true;
        if(typeof prop === 'object' && matchAnything(prop, query)) return true;
    }
    return false;
}

function ListController(url) {
    return function($scope, $http) {
        $scope.page = 1;
        var rules = [];
        var pageSize = 10;
        var itemCount = 0;
        $scope.getPage = function() {
            var res = [];
            if ($scope.query) {
                for (var i in rules) {
                    var rule = rules[i];
                    if (matchAnything(rule, $scope.query)) {
                        res.push(rule);
                    }
                }

            } else {
                res = rules;
            }
            $scope.pages = range(1, Math.ceil(res.length / pageSize));
            $scope.page = Math.min($scope.page, $scope.pages.length);
            return res.slice(($scope.page - 1) * pageSize, $scope.page * pageSize);
        };
        $scope.setPage = function(page) {
            $scope.page = page;
        };
        $scope.nextPage = function() {
            $scope.page = Math.min($scope.page + 1, $scope.pages.length);
        };
        $scope.prevPage = function() {
            $scope.page = Math.max($scope.page - 1, 1);
        };
        $http.get(url).success(function success(data) {
            rules = data;
            $scope.pages = range(1, Math.ceil(data.length / pageSize));
        });
    }
}
