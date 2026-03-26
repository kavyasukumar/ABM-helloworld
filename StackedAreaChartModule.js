var StackedAreaChartModule = function(seriesConfig, canvasWidth, canvasHeight) {
    var self = this;
    var chart = null;
    var datasets = [];

    // 1. Build the DOM elements immediately
    var container = document.createElement("div");
    container.style.width = "100%";
    container.style.maxWidth = canvasWidth + "px";
    container.style.margin = "0 auto";
    
    var canvas = document.createElement("canvas");
    canvas.width = canvasWidth;
    canvas.height = canvasHeight;
    container.appendChild(canvas);
    document.getElementById("elements").appendChild(container);

    var ctx = canvas.getContext("2d");

    // 2. Function to initialize the chart once the library is loaded
    function initChart() {
        if (typeof Chart === 'undefined') {
            // If Chart.js isn't ready, wait 50ms and try again
            setTimeout(initChart, 50);
            return;
        }

        datasets = seriesConfig.map(function(s) {
            return {
                label: s.Label,
                backgroundColor: s.Color,
                borderColor: s.Color,
                data: [],
                fill: true,          
                pointRadius: 0       
            };
        });

        chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    xAxes: [{ display: true }],
                    yAxes: [{ stacked: true, display: true }]
                }
            }
        });
    }

    initChart();

    // 3. Define the Mesa hooks with safety checks
    this.render = function(step_data) {
        if (!chart) return; // Don't render if chart isn't ready
        
        chart.data.labels.push(chart.data.labels.length);
        for (var i = 0; i < datasets.length; i++) {
            datasets[i].data.push(step_data[i]);
        }
        chart.update();
    };
    
    this.reset = function() {
        if (!chart) return;
        
        chart.data.labels = [];
        for (var i = 0; i < datasets.length; i++) {
            datasets[i].data = [];
        }
        chart.update();
    };
};