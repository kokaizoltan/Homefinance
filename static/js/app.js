/* HomeFinance – grafikonok és kisebb interakciók */
(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", function () {
        initCharts();
    });

    function hideCanvas(canvas) {
        if (!canvas) {
            return;
        }
        canvas.classList.add("d-none");
        var box = canvas.parentElement;
        var fallback = box ? box.querySelector("[data-chart-fallback]") : null;
        if (fallback) {
            fallback.classList.remove("d-none");
        }
    }

    function initCharts() {
        var dataElement = document.getElementById("chart-data");
        var canvases = document.querySelectorAll("[data-chart-canvas]");

        if (!canvases.length) {
            return;
        }

        if (typeof Chart === "undefined" || !dataElement) {
            canvases.forEach(hideCanvas);
            return;
        }

        var data;
        try {
            data = JSON.parse(dataElement.textContent);
        } catch (error) {
            canvases.forEach(hideCanvas);
            return;
        }

        Chart.defaults.font.family =
            "'Segoe UI', system-ui, -apple-system, 'Helvetica Neue', Arial, sans-serif";
        Chart.defaults.color = "#64748b";
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.legend.labels.boxWidth = 8;

        var formatter = new Intl.NumberFormat("hu-HU");

        function moneyTooltip(context) {
            var value =
                context.parsed && typeof context.parsed === "object"
                    ? context.parsed.y
                    : context.parsed;
            var label = context.dataset.label ? context.dataset.label + ": " : "";
            return label + formatter.format(value || 0) + " Ft";
        }

        function hasValues(dataset) {
            return (
                dataset &&
                Array.isArray(dataset.values) &&
                dataset.values.some(function (value) {
                    return Number(value) > 0;
                })
            );
        }

        function buildDoughnut(canvasId, dataset, palette) {
            var canvas = document.getElementById(canvasId);
            if (!canvas) {
                return;
            }
            if (!hasValues(dataset)) {
                hideCanvas(canvas);
                return;
            }

            new Chart(canvas, {
                type: "doughnut",
                data: {
                    labels: dataset.labels,
                    datasets: [
                        {
                            data: dataset.values,
                            backgroundColor: palette,
                            borderColor: "#ffffff",
                            borderWidth: 2,
                            hoverOffset: 6,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "58%",
                    plugins: {
                        legend: {
                            position: "bottom",
                            labels: { padding: 14, font: { size: 11 } },
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    var values = context.dataset.data || [];
                                    var total = values.reduce(function (sum, value) {
                                        return sum + Number(value);
                                    }, 0);
                                    var percent = total
                                        ? ((Number(context.parsed) / total) * 100)
                                              .toFixed(1)
                                              .replace(".", ",")
                                        : "0";
                                    return (
                                        context.label +
                                        ": " +
                                        formatter.format(context.parsed) +
                                        " Ft (" +
                                        percent +
                                        "%)"
                                    );
                                },
                            },
                        },
                    },
                },
            });
        }

        var trendCanvas = document.getElementById("trendChart");
        if (trendCanvas && data.trend && data.trend.length) {
            new Chart(trendCanvas, {
                type: "bar",
                data: {
                    labels: data.trend.map(function (row) {
                        return row.label;
                    }),
                    datasets: [
                        {
                            label: "Bevétel",
                            data: data.trend.map(function (row) {
                                return row.income;
                            }),
                            backgroundColor: "rgba(25, 135, 84, 0.78)",
                            hoverBackgroundColor: "rgba(25, 135, 84, 1)",
                            borderRadius: 6,
                            maxBarThickness: 34,
                        },
                        {
                            label: "Kiadás",
                            data: data.trend.map(function (row) {
                                return row.expense;
                            }),
                            backgroundColor: "rgba(220, 53, 69, 0.72)",
                            hoverBackgroundColor: "rgba(220, 53, 69, 1)",
                            borderRadius: 6,
                            maxBarThickness: 34,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: "index", intersect: false },
                    scales: {
                        x: { grid: { display: false } },
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function (value) {
                                    return formatter.format(value);
                                },
                            },
                            grid: { color: "rgba(148, 163, 184, 0.18)" },
                        },
                    },
                    plugins: {
                        legend: { position: "bottom" },
                        tooltip: {
                            callbacks: {
                                label: moneyTooltip,
                            },
                        },
                    },
                },
            });
        } else if (trendCanvas) {
            hideCanvas(trendCanvas);
        }

        var expensePalette = [
            "#dc3545",
            "#fd7e14",
            "#f0ad4e",
            "#d63384",
            "#6f42c1",
            "#0d6efd",
            "#0dcaf0",
            "#6c757d",
            "#adb5bd",
            "#495057",
        ];
        var incomePalette = [
            "#198754",
            "#20c997",
            "#0dcaf0",
            "#0d6efd",
            "#6610f2",
            "#20c997",
            "#94d3a2",
            "#6c757d",
        ];

        buildDoughnut("expenseChart", data.expense, expensePalette);
        buildDoughnut("incomeChart", data.income, incomePalette);
    }
})();
