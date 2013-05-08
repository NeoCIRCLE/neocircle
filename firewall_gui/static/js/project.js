function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
var csrftoken = getCookie('csrftoken');

function csrfSafeMethod(method) {
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}
$.ajaxSetup({
    crossDomain: false,
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type)) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

/**
 * List of firewall collections, controllers/routes will be dynamically created from them.
 *
 * E.g., from the `rule` controller, the RESTful url `/rules/` will be generated,
 * and the `/static/partials/rule-list.html` template will be used.
 * @type {Array}
 */
var controllers = {
    rule: function($scope) {
        $('#targetName').typeahead({
            source: function(query, process) {
                $.ajax({
                    url: '/firewall/autocomplete/' + data.target.type + '/',
                    type: 'post',
                    data: 'name=' + query,
                    success: function autocompleteSuccess(data) {
                        process(data.map(function(obj) {
                            return obj.name;
                        }));
                    }
                });
            },
            matcher: function() {
                return true;
            }
        });
    },
    host: function($scope) {
        $scope.addHostGroup = function(group) {
            for (var i in $scope.entity.groups) {
                var group_ = $scope.entity.groups[i];
                if (group_.name == group && group_.__destroyed) {
                    group_.__destroyed = false;
                    return;
                } else if (group_.name == group) {
                    return;
                }
            }
            console.log('2foooo');
            $scope.entity.groups.push({
                name: group,
                __created: true,
            })
        }
        $scope.removeHostGroup = function(group) {
            console.log(group);
            for (var i in $scope.entity.groups) {
                var group_ = $scope.entity.groups[i];
                if (group_.name == group.name) {
                    group_.__destroyed = true;
                    return;
                }
            }
        }
    },
    vlan: function() {},
    vlangroup: function() {},
    hostgroup: function() {},
    firewall: function() {},
    domain: function() {},
    record: function() {},
    blacklist: function() {},
}
var module = angular.module('firewall', []).config(
['$routeProvider', function($routeProvider) {
    for (var controller in controllers) {
        var init = controllers[controller];
        $routeProvider.when('/' + controller + 's/', {
            templateUrl: '/static/partials/' + controller + '-list.html',
            controller: ListController('/firewall/' + controller + 's/')
        }).when('/' + controller + 's/:id/', {
            templateUrl: '/static/partials/' + controller + '-edit.html',
            controller: EntityController('/firewall/' + controller + 's/', init)
        });
    }
    $routeProvider.otherwise({
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
    for (var i in obj) {
        var prop = obj[i];
        if (typeof prop === 'number' && prop == query) return true;
        if (typeof prop === 'string' && prop.match(expr)) return true;
        if (typeof prop === 'object' && matchAnything(prop, query)) return true;
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

function EntityController(url, init) {
    return function($scope, $http, $routeParams) {
        init($scope);
        var id = $routeParams.id;

        $scope.destroyed = function(item) {
            return !item.__destroyed;
        }
        $http.get(url + id + '/').success(function success(data) {
            $scope.entity = data;
            ['vlan', 'vlangroup', 'host', 'hostgroup', 'firewall'].forEach(function(t) {
                $('.' + t).typeahead({
                    source: function(query, process) {
                        $.ajax({
                            url: '/firewall/autocomplete/' + t + '/',
                            type: 'post',
                            data: 'name=' + query,
                            success: function autocompleteSuccess(data) {
                                process(data.map(function(obj) {
                                    return obj.name;
                                }));
                            }
                        });
                    },
                    matcher: function() {
                        return true;
                    }
                });
            })
        });
    }
}
