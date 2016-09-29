$(function() {
  var data = JSON.parse($("#chart-data").data("data"));
  var labels = [];
  for(var i=0; i<data.labels.length; i++) {
    labels.push(data.labels[i] + " (" + data.readable_data[i] + ")");
  }
  var pieChart = new Chart(document.getElementById("datastore-chart"), {
      type: 'pie',
      data: {
        labels: labels,
        datasets: [{
          data: data['data'],
          backgroundColor: [
              "#57b257",
              "#538ccc",
              "#f0df24",
              "#ff9a38",
              "#7f7f7f",
          ]
        }]
      },
      options: {
        legend: {
          display: false,
        },
        tooltips: {
          callbacks: {
            label: function(item, chartData) {
              return data['labels'][item.index] + ": " + data['readable_data'][item.index];
            }
          }
        },
      }
  });
  $("#datastore-chart-legend").html(pieChart.generateLegend());
});
