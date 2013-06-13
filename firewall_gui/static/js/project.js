/**
 * Getter for user cookies
 * @param  {String} name Cookie name
 * @return {String}      Cookie value
 */

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
/**
 * Extract CSRF token for AJAX calls
 */
var csrftoken = getCookie('csrftoken');

function csrfSafeMethod(method) {
  return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}
$.ajaxSetup({
  crossDomain: false,
  beforeSend: function(xhr, settings) {
    //attach CSRF token to every AJAX call
    if (!csrfSafeMethod(settings.type)) {
      xhr.setRequestHeader("X-CSRFToken", csrftoken);
    }
  }
});

/**
 * Collection handling boilerplate code
 *
 * New entity gets __created flag, deleted entity gets __destoryed flag,
 * so on the server-side we know what changed
 * @param  Object $scope AngularJS scope
 * @param  String name   Object name, add{name} and remove{name} methods will be generated
 * @param  Object model  Model name (the collections name) in the entity
 */

function makeAddRemove($scope, name, model) {
  /**
   * Add entity to collection
   * @param  String entity Name of the entity
   */
  $scope['add' + name] = function(entity) {
    //check if already exists
    for (var i in $scope.entity[model]) {
      var item = $scope.entity[model][i];
      //if it was removed previously, just remove the destroyed flag
      if (item.name == entity && item.__destroyed) {
        item.__destroyed = false;
        return;
      } else if (item.name == entity) {
        //if it is already in the collection, do nothing
        return;
      }
    }
    //add the new entity, with the proper created flag
    $scope.entity[model].push({
      name: entity,
      __created: true,
    });
  }
  /**
   * Remove entity from collection
   * @param  Object entity
   */
  $scope['remove' + name] = function(entity) {
    for (var i in $scope.entity[model]) {
      var item = $scope.entity[model][i];
      //if it was not saved on the server before, just remove it
      if (item.name == entity.name && item.__created) {
        $scope.entity[model].splice(i, 1);
      } else if (item.name == entity.name) {
        //else just set the destoryed flag
        item.__destroyed = true;
        return;
      }
    }
  }
}

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
          url: '/firewall/autocomplete/' + $scope.entity.target.type + '/',
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
      },
      updater: function(item) {
        var self = this;
        $scope.$apply(function() {
          $scope.entity.target.name = item;
        })
        return item;
      }
    });
  },
  host: function($scope) {
    makeAddRemove($scope, 'HostGroup', 'groups');
  },
  vlan: function($scope) {
    makeAddRemove($scope, 'Vlan', 'vlans');
  },
  vlangroup: function($scope) {
    makeAddRemove($scope, 'Vlan', 'vlans');
  },
  hostgroup: function() {},
  firewall: function() {},
  domain: function() {},
  record: function() {},
  blacklist: function() {},
}
/**
 * Configures AngularJS with the defined controllers
 */
var module = angular.module('firewall', []).config(
['$routeProvider',
  function($routeProvider) {
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
  }
]);

/**
 * Generate range [a, b)
 * @param  {Number} a Lower limit
 * @param  {Number} b Upper limit
 * @return {Array}   Number from a to b
 */

function range(a, b) {
  var res = [];
  do res.push(a++);
  while (a <= b)
  return res;
}

/**
 * Smart (recursive) match function for any object
 * @param  {Object} obj    Object to be checked
 * @param  {String} query  Regexp to be checked against
 * @return {Boolean}       True, if object matches (somehow) with query
 */

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

/**
 * Factory for the given collection URL
 * @param  {String} url REST endpoint for collection
 * @return {Function}   ListController for the given REST endpoint
 */

function ListController(url) {
  /**
   * ListController for the given REST endpoint
   * @param  {Object} $scope Current controllers scope
   * @param  {Object} $http  Helper for AJAX calls
   */
  return function($scope, $http) {
    $scope.page = 1;
    var rules = [];
    var pageSize = 100;
    var itemCount = 0;
    /**
     * Does filtering&paging
     * @return {Array} Items to be displayed
     */
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
    /**
     * Setter for current page
     * @param {Number} page Page to navigate to
     */
    $scope.setPage = function(page) {
      $scope.page = page;
    };
    /**
     * Jumps to the next page (if available)
     */
    $scope.nextPage = function() {
      $scope.page = Math.min($scope.page + 1, $scope.pages.length);
    };
    /**
     * Jumps to the previous page (if available)
     */
    $scope.prevPage = function() {
      $scope.page = Math.max($scope.page - 1, 1);
    };

    /**
     * Delete the given entity, then reload the list
     * @param  Number id
     */
    $scope.deleteEntity = function(id) {
      $.ajax({
        url: url.split('/')[2] + '/' + id + '/delete/',
        type: 'post',
        success: reloadList
      });
    };

    /**
     * Reloads the entities
     */

    function reloadList() {
      $http.get(url).success(function success(data) {
        rules = data;
        $scope.pages = range(1, Math.ceil(data.length / pageSize));
      });
    }

    // Initial load...
    reloadList();
  }
}

/**
 * Factory for the given URL
 * @param {Object} url  REST endpoint of the model
 * @param {Object} init Init function for model-specic behaviour
 */

function EntityController(url, init) {
  /**
   * Entity Controller for the given model URL
   * @param  {Object} $scope       Current controllers scope
   * @param  {Object} $http        Helper for AJAX calls
   * @param  {Object} $routeParams Helper for route parameter parsing
   */
  return function($scope, $http, $routeParams) {
    init($scope);
    var id = $routeParams.id;
    $scope.errors = {};
    /**
     * Generic filter for collections
     *
     * Hides destroyed items
     * @param  {Object} item Current item in collection
     * @return {Boolean}     Item should be displayed, or not
     */
    $scope.destroyed = function(item) {
      return !item.__destroyed;
    }
    $scope.hasError = function(name) {
      return $scope.errors[name] ? 'error' : null;
    }
    $scope.getError = function(name) {
      return $scope.errors[name] ? $scope.errors[name] : '';
    }
    $scope.save = function() {
      $scope.errors = {};
      $.ajax({
        url: url + 'save/',
        type: 'post',
        data: JSON.stringify($scope.entity),
        success: function(data) {
          console.log(data);
          var audio = new Audio();
          audio.src = '/static/img/yeah.mp3';
          audio.play();
          $('button[type=submit]').addClass('btn-success');
          setTimeout(function(){
            $('button[type=submit]').removeClass('btn-success');
          }, 4000);
          $scope.$apply(function() {
            $scope.errors = {};
          });
          window.location.hash = '/' + url.split('/')[2] + '/' + data + '/';
        }
      }).error(function(data) {
        try {
          var audio = new Audio();
          audio.src = '/static/img/trombone.ogg';
          audio.play();
          data = JSON.parse(data.responseText);
          $('button[type=submit]').addClass('btn-danger');
          setTimeout(function(){
            $('button[type=submit]').removeClass('btn-danger');
          }, 4000);
          var newErrors = {};
          for (var i in data) {
            var id = $('#' + i).length ? i : 'targetName';
            newErrors[id] = data[i];
          }
          $scope.$apply(function() {
            $scope.errors = newErrors;
          })
        } catch (ex) {
        }
      })
    }

    function reloadEntity() {
      $http.get(url + id + '/').success(function success(data) {
        $scope.entity = data;
        $('input[type=text], input[type=number], select, textarea, .has-tooltip').tooltip({
          placement: 'right'
        });
        ['vlan', 'vlangroup', 'host', 'hostgroup', 'firewall', 'owner', 'domain', 'record'].forEach(function(t) {
          $('.' + t).typeahead({
            /**
             * Typeahead does AJAX queries.
             *
             * Pretty messy
             * @param  {String}   query   Partial name of the entity
             * @param  {Function} process Callback function after AJAX returned result
             */
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
            /**
             * Filtering is done on server-side, show all results
             * @return {Boolean} Always true, so all result are visible
             */
            matcher: function() {
              return true;
            },
            /**
             * The DOM is correctly updated, but it doesnt triggers the proper events,
             * so the model should be updated manually.
             *
             * @param  {String} item Selected entity name
             * @return {String}      Same as `item`, the input value is set to this
             */
            updater: function(item) {
              var self = this;
              console.log(this);
              $scope.$apply(function() {
                var model = self.$element[0].getAttribute('ng-model').split('.')[1];
                console.log(self.$element[0].getAttribute('ng-model'), model);
                try {
                  $scope.entity[model].name = item;
                } catch (ex) {
                  try {
                    $scope[self.$element[0].getAttribute('ng-model')] = item;
                  } catch (ex) {

                  }
                }
              })
              return item;
            }
          });
        })
      });
    }
    reloadEntity();
  }
}
