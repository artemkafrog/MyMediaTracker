// Подключаем ThemeManager
if (typeof ThemeManager === 'undefined') {
    console.warn('ThemeManager not loaded, using fallback');
}

const app = new Vue({
    el: '#app',
    
    data() {
        return {
            loading: false,
            darkMode: ThemeManager ? ThemeManager.isDark() : true,
            
            stats: {
                total_items: 0,
                avg_rating: 0,
                total_duration: 0,
                unique_genres: 0,
                status_counts: {},
                genre_counts: {},
                year_counts: {}
            },
            
            statusData: [],
            genreData: [],
            yearData: [],
            ratingData: [],
            topRated: [],
            watchingItems: [],
            watchingList: [],
            favorites: [],
            allItems: [],
            
            statusChart: null,
            ratingChart: null,
            genreChart: null,
            yearChart: null,
            
            lastUpdated: new Date().toLocaleString(),
            
            toasts: [],
            toastId: 0,
            
            showReportsModal: false,
            showReportViewer: false,
            reports: [],
            reportsLoading: false,
            currentReport: { name: '', content: '' },
            
            showChartsModal: false,
            showChartViewer: false,
            charts: [],
            chartsLoading: false,
            currentChart: { name: '', url: '' }
        };
    },
    
    computed: {
        mostCommonStatus() {
            if (this.statusData.length === 0) return null;
            return this.statusData.reduce((a, b) => a.count > b.count ? a : b);
        },
        
        formatDuration() {
            return (minutes) => {
                if (!minutes || minutes === 0) return '0 min';
                if (minutes < 60) return minutes + ' min';
                const hours = Math.floor(minutes / 60);
                const mins = minutes % 60;
                return hours + 'h ' + mins + 'm';
            };
        },
        
        statusColors() {
            return {
                'watched': '#4CAF50',
                'watching': '#FFB74D',
                'planned': '#64B5F6',
                'on_hold': '#EF5350'
            };
        },
        
        getStatusLabel() {
            const labels = {
                'watched': 'Watched',
                'watching': 'Watching',
                'planned': 'Planned',
                'on_hold': 'On Hold'
            };
            return (status) => labels[status] || status;
        },
        
        favoritesList() {
            if (!this.allItems || this.allItems.length === 0) return [];
            if (!this.favorites || this.favorites.length === 0) return [];
            
            const result = this.allItems.filter(item => this.favorites.includes(item.id));
            return result;
        },
        
        watchingItemsList() {
            if (!this.allItems || this.allItems.length === 0) return [];
            
            const history = JSON.parse(localStorage.getItem('watchHistory') || '{}');
            const result = this.allItems.filter(item => {
                if (item.status === 'watched') return false;
                const progress = this.getWatchProgress(item);
                return progress > 0 && progress < 100;
            });
            
            return result.sort((a, b) => {
                const aTime = history[a.id]?.lastWatched || 0;
                const bTime = history[b.id]?.lastWatched || 0;
                return bTime - aTime;
            });
        }
    },
    
    mounted() {
        this.loadAnalytics();
        this.loadReports();
        this.loadCharts();
        this.setupKeyboardShortcuts();
        
        if (!this.darkMode) {
            document.body.classList.add('light-theme');
            document.getElementById('app').classList.add('light-theme');
        }
        
        const storedFavorites = JSON.parse(localStorage.getItem('favorites') || '[]');
        console.log('Stored favorites from localStorage:', storedFavorites);
        
        // Слушаем изменения темы из других вкладок/приложений
        document.addEventListener('themeChanged', this.onThemeChanged);
    },
    
    beforeDestroy() {
        this.destroyCharts();
        document.removeEventListener('themeChanged', this.onThemeChanged);
    },
    
    methods: {
        onThemeChanged(e) {
            this.darkMode = e.detail.darkMode;
            setTimeout(() => {
                this.renderCharts();
            }, 100);
        },
        
        async loadAnalytics() {
            this.loading = true;
            
            try {
                const [statsRes, itemsRes] = await Promise.all([
                    fetch('/api/analytics/stats'),
                    fetch('/api/items')
                ]);
                
                const statsData = await statsRes.json();
                const itemsData = await itemsRes.json();
                
                const storedFavorites = JSON.parse(localStorage.getItem('favorites') || '[]');
                this.favorites = storedFavorites;
                console.log('Favorites loaded from localStorage:', this.favorites);
                
                if (statsData.success) {
                    this.stats = statsData.stats;
                    this.statusData = statsData.status_data || [];
                    this.genreData = statsData.genre_data || [];
                    this.yearData = statsData.year_data || [];
                    this.ratingData = statsData.rating_data || [];
                    this.topRated = statsData.top_rated || [];
                }
                
                if (itemsData.success) {
                    this.allItems = itemsData.items;
                    console.log('All items loaded:', this.allItems.length);
                    
                    this.watchingItems = this.allItems.filter(item => {
                        if (item.status !== 'watching') return false;
                        const progress = this.getWatchProgress(item);
                        return progress > 0;
                    });
                    
                    this.watchingList = this.watchingItemsList;
                    console.log('Watching items with progress:', this.watchingList);
                }
                
                this.lastUpdated = new Date().toLocaleString();
                this.$nextTick(() => {
                    this.renderCharts();
                });
                
            } catch (error) {
                console.error('Error loading analytics:', error);
                this.showToast('Error loading analytics data', 'error');
            } finally {
                this.loading = false;
            }
        },
        
        async loadReports() {
            this.reportsLoading = true;
            try {
                const response = await fetch('/api/reports/list');
                const data = await response.json();
                if (data.success) {
                    this.reports = data.reports;
                }
            } catch (error) {
                console.error('Error loading reports:', error);
            } finally {
                this.reportsLoading = false;
            }
        },
        
        async loadCharts() {
            this.chartsLoading = true;
            try {
                const response = await fetch('/api/charts/list');
                const data = await response.json();
                if (data.success) {
                    this.charts = data.charts.map(chart => ({
                        ...chart,
                        url: `/api/charts/view/${chart.name}`
                    }));
                    console.log('Charts loaded:', this.charts);
                } else {
                    console.error('Failed to load charts:', data.error);
                }
            } catch (error) {
                console.error('Error loading charts:', error);
            } finally {
                this.chartsLoading = false;
            }
        },
        
        handleImageError(event) {
            event.target.style.display = 'none';
            const parent = event.target.parentElement;
            const fallback = document.createElement('span');
            fallback.className = 'preview-icon';
            fallback.textContent = '🖼️';
            parent.appendChild(fallback);
            this.showToast('Failed to load image: ' + event.target.src, 'error');
        },

        renderCharts() {
            this.destroyCharts();
            this.renderStatusChart();
            this.renderRatingChart();
            this.renderGenreChart();
            this.renderYearChart();
        },
        
        renderStatusChart() {
            const ctx = document.getElementById('statusChart')?.getContext('2d');
            if (!ctx) return;
            
            const labels = this.statusData.map(d => d.label);
            const data = this.statusData.map(d => d.count);
            const colors = {
                'watched': '#4CAF50',
                'watching': '#FFB74D',
                'planned': '#64B5F6',
                'on_hold': '#EF5350'
            };
            
            const backgroundColors = this.statusData.map(d => colors[d.value] || '#6B6B6B');
            
            this.statusChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: backgroundColors,
                        borderColor: this.darkMode ? '#141414' : '#FFFFFF',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                color: this.darkMode ? '#A1A1A1' : '#666666',
                                padding: 12,
                                usePointStyle: true,
                                pointStyle: 'circle'
                            }
                        }
                    },
                    cutout: '70%'
                }
            });
        },
        
        renderRatingChart() {
            const ctx = document.getElementById('ratingChart')?.getContext('2d');
            if (!ctx) return;
            
            const labels = this.ratingData.map(d => d.label);
            const data = this.ratingData.map(d => d.count);
            
            this.ratingChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Items',
                        data: data,
                        backgroundColor: this.darkMode ? 'rgba(217, 122, 58, 0.6)' : 'rgba(217, 122, 58, 0.5)',
                        borderColor: '#D97A3A',
                        borderWidth: 1,
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                color: this.darkMode ? '#6B6B6B' : '#888888',
                                stepSize: 1
                            },
                            grid: {
                                color: this.darkMode ? '#1A1A1A' : '#E5E5E5'
                            }
                        },
                        x: {
                            ticks: {
                                color: this.darkMode ? '#6B6B6B' : '#888888'
                            },
                            grid: {
                                display: false
                            }
                        }
                    }
                }
            });
        },
        
        renderGenreChart() {
            const ctx = document.getElementById('genreChart')?.getContext('2d');
            if (!ctx) return;
            
            const topGenres = this.genreData.slice(0, 10);
            const labels = topGenres.map(d => d.label);
            const data = topGenres.map(d => d.count);
            
            this.genreChart = new Chart(ctx, {
                type: 'horizontalBar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Items',
                        data: data,
                        backgroundColor: this.darkMode ? 'rgba(100, 181, 246, 0.6)' : 'rgba(100, 181, 246, 0.5)',
                        borderColor: '#64B5F6',
                        borderWidth: 1,
                        borderRadius: 4
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            ticks: {
                                color: this.darkMode ? '#6B6B6B' : '#888888',
                                font: {
                                    size: 11
                                }
                            },
                            grid: {
                                display: false
                            }
                        },
                        x: {
                            beginAtZero: true,
                            ticks: {
                                color: this.darkMode ? '#6B6B6B' : '#888888',
                                stepSize: 1
                            },
                            grid: {
                                color: this.darkMode ? '#1A1A1A' : '#E5E5E5'
                            }
                        }
                    }
                }
            });
        },
        
        renderYearChart() {
            const ctx = document.getElementById('yearChart')?.getContext('2d');
            if (!ctx) return;
            
            const sorted = [...this.yearData].sort((a, b) => a.label - b.label);
            const labels = sorted.map(d => d.label);
            const data = sorted.map(d => d.count);
            
            const gradient = ctx.createLinearGradient(0, 0, 0, 200);
            gradient.addColorStop(0, this.darkMode ? 'rgba(217, 122, 58, 0.6)' : 'rgba(217, 122, 58, 0.4)');
            gradient.addColorStop(1, this.darkMode ? 'rgba(217, 122, 58, 0.0)' : 'rgba(217, 122, 58, 0.0)');
            
            this.yearChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Releases',
                        data: data,
                        backgroundColor: gradient,
                        borderColor: '#D97A3A',
                        borderWidth: 2,
                        pointBackgroundColor: '#D97A3A',
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        fill: true,
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                color: this.darkMode ? '#6B6B6B' : '#888888',
                                stepSize: 1
                            },
                            grid: {
                                color: this.darkMode ? '#1A1A1A' : '#E5E5E5'
                            }
                        },
                        x: {
                            ticks: {
                                color: this.darkMode ? '#6B6B6B' : '#888888',
                                maxTicksLimit: 15,
                                autoSkip: true
                            },
                            grid: {
                                display: false
                            }
                        }
                    }
                }
            });
        },
        
        destroyCharts() {
            if (this.statusChart) {
                this.statusChart.destroy();
                this.statusChart = null;
            }
            if (this.ratingChart) {
                this.ratingChart.destroy();
                this.ratingChart = null;
            }
            if (this.genreChart) {
                this.genreChart.destroy();
                this.genreChart = null;
            }
            if (this.yearChart) {
                this.yearChart.destroy();
                this.yearChart = null;
            }
        },
        
        getWatchProgress(item) {
            const history = JSON.parse(localStorage.getItem('watchHistory') || '{}');
            if (!history[item.id]) return 0;
            return Math.min(Math.round(history[item.id].progress || 0), 100);
        },
        
        async refreshData() {
            await this.loadAnalytics();
            await this.loadReports();
            await this.loadCharts();
            this.showToast('Analytics data refreshed', 'success');
        },
        
        async generateCharts() {
            this.loading = true;
            try {
                const response = await fetch('/api/analytics/generate', {
                    method: 'POST'
                });
                const data = await response.json();
                
                if (data.success) {
                    this.showToast('Charts generated successfully', 'success');
                    await this.loadReports();
                    await this.loadCharts();
                    await this.loadAnalytics();
                } else {
                    this.showToast(data.error || 'Generation failed', 'error');
                }
            } catch (error) {
                console.error('Error generating charts:', error);
                this.showToast('Generation error', 'error');
            } finally {
                this.loading = false;
            }
        },
        
        async exportReport() {
            try {
                const response = await fetch('/api/analytics/export');
                const data = await response.json();
                
                if (data.success) {
                    const blob = await (await fetch(data.url)).blob();
                    const link = document.createElement('a');
                    link.href = URL.createObjectURL(blob);
                    const filename = data.url.split('/').pop() || 'analytics_report.json';
                    link.download = filename;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    setTimeout(() => URL.revokeObjectURL(link.href), 100);
                    this.showToast('Report exported successfully', 'success');
                } else {
                    this.showToast(data.error || 'Export failed', 'error');
                }
            } catch (error) {
                console.error('Error exporting report:', error);
                this.showToast('Export error', 'error');
            }
        },
        
        async viewReport(report) {
            try {
                const response = await fetch('/api/reports/view/' + report.name);
                const data = await response.json();
                if (data.success) {
                    this.currentReport = {
                        name: report.name,
                        content: data.content
                    };
                    this.showReportViewer = true;
                } else {
                    this.showToast(data.error || 'Failed to view report', 'error');
                }
            } catch (error) {
                console.error('Error viewing report:', error);
                this.showToast('Error viewing report', 'error');
            }
        },
        
        async deleteReport(report) {
            if (!confirm('Delete "' + report.name + '"?')) return;
            
            try {
                const response = await fetch('/api/reports/delete/' + report.name, {
                    method: 'DELETE'
                });
                const data = await response.json();
                
                if (data.success) {
                    this.reports = this.reports.filter(r => r.name !== report.name);
                    this.showToast('Report deleted', 'success');
                } else {
                    this.showToast(data.error || 'Delete failed', 'error');
                }
            } catch (error) {
                console.error('Error deleting report:', error);
                this.showToast('Delete error', 'error');
            }
        },
        
        async deleteAllReports() {
            if (this.reports.length === 0) return;
            if (!confirm('Delete all ' + this.reports.length + ' reports?')) return;
            
            try {
                const response = await fetch('/api/reports/delete-all', {
                    method: 'DELETE'
                });
                const data = await response.json();
                
                if (data.success) {
                    this.reports = [];
                    this.showToast('All reports deleted', 'success');
                } else {
                    this.showToast(data.error || 'Delete failed', 'error');
                }
            } catch (error) {
                console.error('Error deleting reports:', error);
                this.showToast('Delete error', 'error');
            }
        },
        
        async downloadReport(report) {
            try {
                const response = await fetch('/api/reports/download/' + report.name);
                const blob = await response.blob();
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = report.name;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                setTimeout(() => URL.revokeObjectURL(link.href), 100);
                this.showToast('Report downloaded: ' + report.name, 'success');
            } catch (error) {
                console.error('Error downloading report:', error);
                this.showToast('Download error', 'error');
            }
        },
        
        // === CHART METHODS ===
        async viewChart(chart) {
            if (!chart.url) {
                this.showToast('Chart URL not found', 'error');
                return;
            }
            this.currentChart = chart;
            this.showChartViewer = true;
        },
        
        async deleteChart(chart) {
            if (!confirm('Delete "' + chart.name + '"?')) return;
            
            try {
                const response = await fetch('/api/charts/delete/' + chart.name, {
                    method: 'DELETE'
                });
                const data = await response.json();
                
                if (data.success) {
                    this.charts = this.charts.filter(c => c.name !== chart.name);
                    this.showToast('Chart deleted', 'success');
                } else {
                    this.showToast(data.error || 'Delete failed', 'error');
                }
            } catch (error) {
                console.error('Error deleting chart:', error);
                this.showToast('Delete error', 'error');
            }
        },
        
        async deleteAllCharts() {
            if (this.charts.length === 0) return;
            if (!confirm('Delete all ' + this.charts.length + ' charts?')) return;
            
            try {
                const response = await fetch('/api/charts/delete-all', {
                    method: 'DELETE'
                });
                const data = await response.json();
                
                if (data.success) {
                    this.charts = [];
                    this.showToast('All charts deleted', 'success');
                } else {
                    this.showToast(data.error || 'Delete failed', 'error');
                }
            } catch (error) {
                console.error('Error deleting charts:', error);
                this.showToast('Delete error', 'error');
            }
        },
        
        async downloadChart(chart) {
            try {
                const response = await fetch('/api/charts/download/' + chart.name);
                const blob = await response.blob();
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = chart.name;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                setTimeout(() => URL.revokeObjectURL(link.href), 100);
                this.showToast('Chart downloaded: ' + chart.name, 'success');
            } catch (error) {
                console.error('Error downloading chart:', error);
                try {
                    const response = await fetch(chart.url);
                    const blob = await response.blob();
                    const link = document.createElement('a');
                    link.href = URL.createObjectURL(blob);
                    link.download = chart.name;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    setTimeout(() => URL.revokeObjectURL(link.href), 100);
                    this.showToast('Chart downloaded: ' + chart.name, 'success');
                } catch (e) {
                    this.showToast('Download error', 'error');
                }
            }
        },
        
        formatFileSize(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        },
        
        formatDate(timestamp) {
            const date = new Date(timestamp);
            return date.toLocaleString();
        },
        
        toggleTheme() {
            if (ThemeManager) {
                this.darkMode = ThemeManager.toggle();
            } else {
                // Fallback
                this.darkMode = !this.darkMode;
                if (this.darkMode) {
                    document.body.classList.remove('light-theme');
                    document.getElementById('app').classList.remove('light-theme');
                } else {
                    document.body.classList.add('light-theme');
                    document.getElementById('app').classList.add('light-theme');
                }
            }
            
            this.renderCharts();
        },
        
        showToast(message, type = 'info') {
            const id = ++this.toastId;
            this.toasts.push({ id, message, type });
            
            setTimeout(() => {
                this.toasts = this.toasts.filter(t => t.id !== id);
            }, 3000);
        },
        
        setupKeyboardShortcuts() {
            document.addEventListener('keydown', (e) => {
                if (e.key === 'r' && !e.ctrlKey && !e.metaKey) {
                    this.refreshData();
                }
                if (e.ctrlKey && e.key === 'e') {
                    e.preventDefault();
                    this.exportReport();
                }
                if (e.key === 'Escape') {
                    this.showReportsModal = false;
                    this.showReportViewer = false;
                    this.showChartsModal = false;
                    this.showChartViewer = false;
                    this.toasts = [];
                }
            });
        }
    },
    
    watch: {
        darkMode() {
            setTimeout(() => {
                this.renderCharts();
            }, 100);
        }
    }
});

// Слушаем изменения темы из других вкладок/приложений
document.addEventListener('themeChanged', (e) => {
    if (app && app.darkMode !== undefined) {
        app.darkMode = e.detail.darkMode;
        setTimeout(() => {
            app.renderCharts();
        }, 100);
    }
});