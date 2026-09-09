/**
 * SMART EXPENSE TRACKER - CHART.JS VISUALIZATION ENGINE
 */

document.addEventListener('DOMContentLoaded', async () => {
    // Check if on dashboard page
    const categoryChartEl = document.getElementById('categoryDoughnutChart');
    if (!categoryChartEl) return;

    try {
        const response = await fetch('/api/chart-data');
        if (!response.ok) return;
        const data = await response.json();

        // Chart.js default dark theme configuration
        Chart.defaults.color = '#94a3b8';
        Chart.defaults.font.family = "'Plus Jakarta Sans', sans-serif";
        Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.9)';
        Chart.defaults.plugins.tooltip.titleColor = '#f8fafc';
        Chart.defaults.plugins.tooltip.bodyColor = '#cbd5e1';
        Chart.defaults.plugins.tooltip.borderColor = 'rgba(255, 255, 255, 0.1)';
        Chart.defaults.plugins.tooltip.borderWidth = 1;
        Chart.defaults.plugins.tooltip.padding = 12;
        Chart.defaults.plugins.tooltip.cornerRadius = 8;

        // 1. Expense by Category (Doughnut Chart)
        if (categoryChartEl) {
            new Chart(categoryChartEl, {
                type: 'doughnut',
                data: {
                    labels: data.category_chart.labels.length ? data.category_chart.labels : ['No Expenses Yet'],
                    datasets: [{
                        data: data.category_chart.datasets[0].data.length ? data.category_chart.datasets[0].data : [1],
                        backgroundColor: data.category_chart.datasets[0].backgroundColor.length ? data.category_chart.datasets[0].backgroundColor : ['#334155'],
                        borderWidth: 2,
                        borderColor: '#111827',
                        hoverOffset: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '70%',
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { boxWidth: 12, padding: 14, font: { size: 11, weight: '500' } }
                        }
                    }
                }
            });
        }

        // 2. Monthly Expense & Income Trend (Line Chart)
        const trendChartEl = document.getElementById('monthlyTrendChart');
        if (trendChartEl) {
            new Chart(trendChartEl, {
                type: 'line',
                data: data.monthly_trend,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    scales: {
                        x: { grid: { color: 'rgba(255, 255, 255, 0.04)' } },
                        y: {
                            grid: { color: 'rgba(255, 255, 255, 0.04)' },
                            ticks: { callback: (val) => '$' + val.toLocaleString() }
                        }
                    },
                    plugins: {
                        legend: { position: 'top', labels: { boxWidth: 12, padding: 14 } }
                    }
                }
            });
        }

        // 3. Income vs Expense Bar Chart
        const barChartEl = document.getElementById('incomeExpenseBarChart');
        if (barChartEl) {
            new Chart(barChartEl, {
                type: 'bar',
                data: {
                    labels: data.monthly_trend.labels,
                    datasets: [
                        {
                            label: 'Income',
                            data: data.monthly_trend.datasets[1].data,
                            backgroundColor: '#10b981',
                            borderRadius: 6
                        },
                        {
                            label: 'Expenses',
                            data: data.monthly_trend.datasets[0].data,
                            backgroundColor: '#ef4444',
                            borderRadius: 6
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { grid: { display: false } },
                        y: {
                            grid: { color: 'rgba(255, 255, 255, 0.04)' },
                            ticks: { callback: (val) => '$' + val.toLocaleString() }
                        }
                    }
                }
            });
        }

        // 4. Budget vs Actual Comparison (Horizontal/Vertical Bar)
        const budgetChartEl = document.getElementById('budgetVsActualChart');
        if (budgetChartEl && data.budget_vs_actual.labels.length > 0) {
            new Chart(budgetChartEl, {
                type: 'bar',
                data: {
                    labels: data.budget_vs_actual.labels,
                    datasets: [
                        {
                            label: 'Budget Limit',
                            data: data.budget_vs_actual.budget,
                            backgroundColor: 'rgba(99, 102, 241, 0.4)',
                            borderColor: '#6366f1',
                            borderWidth: 1,
                            borderRadius: 4
                        },
                        {
                            label: 'Actual Spent',
                            data: data.budget_vs_actual.actual,
                            backgroundColor: 'rgba(239, 68, 68, 0.8)',
                            borderRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y',
                    scales: {
                        x: {
                            grid: { color: 'rgba(255, 255, 255, 0.04)' },
                            ticks: { callback: (val) => '$' + val.toLocaleString() }
                        },
                        y: { grid: { display: false } }
                    }
                }
            });
        }

        // 5. Account Balances Breakdown Chart
        const accountChartEl = document.getElementById('accountBalancesChart');
        if (accountChartEl && data.account_balances.labels.length > 0) {
            new Chart(accountChartEl, {
                type: 'doughnut',
                data: {
                    labels: data.account_balances.labels,
                    datasets: [{
                        data: data.account_balances.balances,
                        backgroundColor: ['#6366f1', '#10b981', '#06b6d4', '#f59e0b', '#8b5cf6', '#ec4899'],
                        borderWidth: 2,
                        borderColor: '#111827'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '60%',
                    plugins: {
                        legend: { position: 'bottom', labels: { boxWidth: 12, padding: 12 } }
                    }
                }
            });
        }

    } catch (err) {
        console.error('Error fetching dashboard chart data:', err);
    }
});
