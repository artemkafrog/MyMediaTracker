const app = new Vue({
    el: '#app',
    
    data() {
        return {
            items: [],
            filteredItems: [],
            loading: false,
            darkMode: true,
            viewMode: 'grid',
            searchQuery: '',
            activeFilter: 'all',
            statusMessage: 'Ready',
            isEditing: false,
            editingId: null,
            
            filters: [
                { value: 'all', label: 'All' },
                { value: 'watched', label: 'Watched' },
                { value: 'watching', label: 'Watching' },
                { value: 'planned', label: 'Planned' },
                { value: 'on_hold', label: 'On Hold' }
            ],
            
            statusOptions: [
                { value: 'watched', label: 'Watched' },
                { value: 'watching', label: 'Watching' },
                { value: 'planned', label: 'Planned' },
                { value: 'on_hold', label: 'On Hold' }
            ],
            
            showAddModal: false,
            showStatsModal: false,
            showPlayer: false,
            selectedItem: null,
            currentVideo: null,
            
            newItem: {
                title: '',
                year: new Date().getFullYear(),
                rating: 5,
                duration: 0,
                genres: '',
                authors: '',
                description: '',
                video_path: '',
                video_url: '',
                status: 'planned'
            },
            
            stats: {
                total: 0,
                by_status: {},
                by_type: {},
                avg_rating: 0,
                total_duration: 0
            },
            
            currentTime: '00:00',
            totalDuration: '00:00',
            isFullscreen: false,
            playerWidth: 80,
            playerHeight: 60,
            
            toasts: [],
            toastId: 0,
            
            favorites: JSON.parse(localStorage.getItem('favorites') || '[]'),
            watchHistory: JSON.parse(localStorage.getItem('watchHistory') || '{}'),
            watchStartTime: null,
            watchInterval: null
        };
    },
    
    computed: {
        getStatusLabel() {
            const labels = {
                'watched': 'Watched',
                'watching': 'Watching',
                'planned': 'Planned',
                'on_hold': 'On Hold'
            };
            return (status) => labels[status] || status;
        },
        
        formatDuration() {
            return (minutes) => {
                if (!minutes || minutes === 0) return 'N/A';
                if (minutes < 60) return minutes + ' min';
                const hours = Math.floor(minutes / 60);
                const mins = minutes % 60;
                return hours + 'h ' + mins + 'm';
            };
        },
        
        playerModalStyle() {
            return {
                maxWidth: this.isFullscreen ? '100%' : '90%',
                width: this.isFullscreen ? '100%' : this.playerWidth + '%',
                height: this.isFullscreen ? '100%' : 'auto',
                maxHeight: this.isFullscreen ? '100%' : '90vh',
                borderRadius: this.isFullscreen ? '0' : '20px',
                padding: this.isFullscreen ? '0' : '32px',
                margin: this.isFullscreen ? '0' : 'auto'
            };
        },
        
        videoContainerStyle() {
            return {
                height: this.isFullscreen ? 'calc(100vh - 160px)' : (this.playerHeight + 'vh'),
                maxHeight: this.isFullscreen ? '100%' : '80vh',
                minHeight: this.isFullscreen ? 'calc(100vh - 160px)' : '300px'
            };
        },
        
        themeIcon() {
            return this.darkMode ? '🌙' : '☀️';
        }
    },
    
    mounted() {
        this.loadItems();
        this.loadStats();
        this.setupKeyboardShortcuts();
        
        if (!this.darkMode) {
            document.body.classList.add('light-theme');
            document.getElementById('app').classList.add('light-theme');
        }
    },
    
    beforeDestroy() {
        this.stopWatchTimer();
    },
    
    methods: {
        async loadItems() {
            this.loading = true;
            this.statusMessage = 'Loading...';
            
            try {
                const response = await fetch('/api/items');
                const data = await response.json();
                
                if (data.success) {
                    this.items = data.items.map(item => ({
                        ...item,
                        favorite: this.favorites.includes(item.id),
                        isUrl: item.video_path && (item.video_path.startsWith('http://') || item.video_path.startsWith('https://'))
                    }));
                    this.applyFilter(this.activeFilter);
                    this.statusMessage = 'Loaded ' + data.items.length + ' items';
                } else {
                    this.showToast(data.error || 'Load error', 'error');
                }
            } catch (error) {
                console.error('Error loading items:', error);
                this.showToast('Error loading data', 'error');
            } finally {
                this.loading = false;
            }
        },
        
        refreshItems() {
            this.loadItems();
            this.loadStats();
            this.showToast('🔄 Data updated', 'success');
        },
        
        async loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                if (data.success) {
                    this.stats = data.stats;
                }
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        },
        
        applyFilter(filterValue) {
            this.activeFilter = filterValue;
            
            if (filterValue === 'all') {
                this.filteredItems = [...this.items];
            } else {
                this.filteredItems = this.items.filter(
                    item => item.status === filterValue
                );
            }
            
            if (this.searchQuery) {
                this.filteredItems = this.filteredItems.filter(item =>
                    item.title.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
                    item.genres.some(g => g.toLowerCase().includes(this.searchQuery.toLowerCase())) ||
                    item.authors.some(a => a.toLowerCase().includes(this.searchQuery.toLowerCase()))
                );
            }
        },
        
        async searchItems() {
            if (!this.searchQuery.trim()) {
                this.applyFilter(this.activeFilter);
                return;
            }
            
            this.loading = true;
            this.statusMessage = 'Searching...';
            
            try {
                const response = await fetch('/api/search?q=' + encodeURIComponent(this.searchQuery));
                const data = await response.json();
                
                if (data.success) {
                    this.filteredItems = data.items.map(item => ({
                        ...item,
                        favorite: this.favorites.includes(item.id),
                        isUrl: item.video_path && (item.video_path.startsWith('http://') || item.video_path.startsWith('https://'))
                    }));
                    this.statusMessage = 'Found ' + data.items.length + ' items';
                } else {
                    this.showToast(data.error || 'Search error', 'error');
                }
            } catch (error) {
                console.error('Error searching:', error);
                this.showToast('Search error', 'error');
            } finally {
                this.loading = false;
            }
        },
        
        getWatchProgress(item) {
            if (!this.watchHistory[item.id]) return 0;
            const progress = this.watchHistory[item.id].progress || 0;
            return Math.min(Math.round(progress), 100);
        },
        
        updateWatchTime(itemId, progress) {
            if (!this.watchHistory[itemId]) {
                this.watchHistory[itemId] = {
                    progress: 0,
                    lastWatched: Date.now()
                };
            }
            this.watchHistory[itemId].progress = Math.max(
                this.watchHistory[itemId].progress || 0,
                progress
            );
            this.watchHistory[itemId].lastWatched = Date.now();
            localStorage.setItem('watchHistory', JSON.stringify(this.watchHistory));
        },
        
        startWatchTimer(item) {
            if (item.status === 'watched') return;
            this.watchStartTime = Date.now();
            if (this.watchInterval) clearInterval(this.watchInterval);
            this.watchInterval = setInterval(() => {
                if (this.currentVideo && this.currentVideo.duration > 0) {
                    const elapsed = (Date.now() - this.watchStartTime) / 1000;
                    const totalSeconds = this.currentVideo.duration * 60;
                    const progress = Math.min((elapsed / totalSeconds) * 100, 95);
                    this.updateWatchTime(this.currentVideo.id, progress);
                }
            }, 5000);
        },
        
        stopWatchTimer() {
            if (this.watchInterval) {
                clearInterval(this.watchInterval);
                this.watchInterval = null;
            }
        },
        
        openAddModal() {
            this.isEditing = false;
            this.editingId = null;
            this.newItem = {
                title: '',
                year: new Date().getFullYear(),
                rating: 5,
                duration: 0,
                genres: '',
                authors: '',
                description: '',
                video_path: '',
                video_url: '',
                status: 'planned'
            };
            this.showAddModal = true;
        },
        
        closeAddModal() {
            this.showAddModal = false;
            this.isEditing = false;
            this.editingId = null;
        },
        
        async saveItem() {
            if (!this.newItem.title.trim()) {
                const now = new Date();
                this.newItem.title = 'Video from ' + now.toLocaleDateString('en-US') + ' ' + now.toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit'});
            }
            
            let videoPath = this.newItem.video_path;
            if (this.newItem.video_url && this.newItem.video_url.trim()) {
                videoPath = this.newItem.video_url.trim();
            }
            
            this.loading = true;
            
            try {
                const url = this.isEditing ? '/api/items/' + this.editingId : '/api/items';
                const method = this.isEditing ? 'PUT' : 'POST';
                
                const response = await fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        ...this.newItem,
                        video_path: videoPath
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    if (this.isEditing) {
                        const index = this.items.findIndex(i => i.id === this.editingId);
                        if (index !== -1) {
                            this.items[index] = {
                                ...data.item,
                                favorite: this.favorites.includes(data.item.id),
                                isUrl: videoPath && (videoPath.startsWith('http://') || videoPath.startsWith('https://'))
                            };
                        }
                    } else {
                        this.items.push({ 
                            ...data.item, 
                            favorite: false,
                            isUrl: videoPath && (videoPath.startsWith('http://') || videoPath.startsWith('https://'))
                        });
                    }
                    this.applyFilter(this.activeFilter);
                    this.closeAddModal();
                    this.loadStats();
                    this.showToast('✅ ' + data.message, 'success');
                    this.statusMessage = this.isEditing ? 'Item updated' : 'Item added';
                } else {
                    this.showToast(data.error || 'Save error', 'error');
                }
            } catch (error) {
                console.error('Error saving item:', error);
                this.showToast('Save error', 'error');
            } finally {
                this.loading = false;
            }
        },
        
        openDetail(item) {
            this.selectedItem = { ...item };
        },
        
        editItem() {
            if (!this.selectedItem) return;
            
            this.isEditing = true;
            this.editingId = this.selectedItem.id;
            this.newItem = {
                title: this.selectedItem.title,
                year: this.selectedItem.year || new Date().getFullYear(),
                rating: this.selectedItem.rating,
                duration: this.selectedItem.duration,
                genres: this.selectedItem.genres.join(', '),
                authors: this.selectedItem.authors.join(', '),
                description: this.selectedItem.description || '',
                video_path: this.selectedItem.video_path || '',
                video_url: '',
                status: this.selectedItem.status
            };
            
            this.selectedItem = null;
            this.showAddModal = true;
        },
        
        async deleteItem(item) {
            if (!confirm('Delete "' + item.title + '"?')) return;
            
            try {
                const response = await fetch('/api/items/' + item.id, {
                    method: 'DELETE'
                });
                
                const data = await response.json();
                
                if (data.success) {
                    this.items = this.items.filter(i => i.id !== item.id);
                    this.applyFilter(this.activeFilter);
                    this.selectedItem = null;
                    this.loadStats();
                    this.showToast('🗑️ ' + data.message, 'success');
                } else {
                    this.showToast(data.error || 'Delete error', 'error');
                }
            } catch (error) {
                console.error('Error deleting item:', error);
                this.showToast('Delete error', 'error');
            }
        },
        
        browseVideo() {
            this.$refs.fileInput.click();
        },
        
        async handleFileUpload(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            const formData = new FormData();
            formData.append('video', file);
            
            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    this.newItem.video_path = '/api/video/' + data.filename;
                    this.newItem.video_url = '';
                    if (data.duration > 0 && !this.newItem.duration) {
                        this.newItem.duration = Math.round(data.duration / 60);
                    }
                    if (!this.newItem.title.trim()) {
                        this.newItem.title = file.name.replace(/\.[^/.]+$/, '');
                    }
                    this.showToast('📤 ' + data.message, 'success');
                } else {
                    this.showToast(data.error || 'Upload error', 'error');
                }
            } catch (error) {
                console.error('Error uploading video:', error);
                this.showToast('Video upload error', 'error');
            }
            
            event.target.value = '';
        },
        
        playVideo(item) {
            if (!item.video_path) {
                this.showToast('Video not found', 'error');
                return;
            }
            
            const isUrl = item.video_path.startsWith('http://') || item.video_path.startsWith('https://');
            
            this.currentVideo = {
                ...item,
                isUrl: isUrl
            };
            this.isFullscreen = false;
            this.playerWidth = 80;
            this.playerHeight = 60;
            this.showPlayer = true;
            this.selectedItem = null;
            
            this.startWatchTimer(item);
        },
        
        closePlayer() {
            this.showPlayer = false;
            this.currentVideo = null;
            this.isFullscreen = false;
            this.stopWatchTimer();
            if (this.$refs.videoPlayer) {
                this.$refs.videoPlayer.pause();
            }
        },
        
        toggleFullscreen() {
            this.isFullscreen = !this.isFullscreen;
            if (this.isFullscreen) {
                this.playerWidth = 100;
                this.playerHeight = 100;
                const video = this.$refs.videoPlayer;
                if (video && video.requestFullscreen) {
                    video.requestFullscreen().catch(() => {});
                }
            } else {
                this.playerWidth = 80;
                this.playerHeight = 60;
                if (document.fullscreenElement) {
                    document.exitFullscreen().catch(() => {});
                }
            }
        },
        
        changePlayerSize(delta) {
            this.playerWidth = Math.max(40, Math.min(95, this.playerWidth + delta));
        },
        
        changePlayerHeight(delta) {
            this.playerHeight = Math.max(30, Math.min(90, this.playerHeight + delta));
        },
        
        updateProgress() {
            const video = this.$refs.videoPlayer;
            if (!video) return;
            
            this.currentTime = this.formatTime(video.currentTime);
            this.totalDuration = this.formatTime(video.duration);
            
            if (this.currentVideo && video.duration > 0) {
                const progress = (video.currentTime / video.duration) * 100;
                if (progress > 0) {
                    this.updateWatchTime(this.currentVideo.id, progress);
                }
            }
        },
        
        onVideoEnded() {
            this.showToast('✅ Playback finished', 'info');
            if (this.currentVideo) {
                this.updateWatchTime(this.currentVideo.id, 100);
            }
            this.stopWatchTimer();
        },
        
        formatTime(seconds) {
            if (!seconds || isNaN(seconds)) return '00:00';
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
        },
        
        toggleFavorite(item) {
            const index = this.favorites.indexOf(item.id);
            if (index === -1) {
                this.favorites.push(item.id);
                item.favorite = true;
                this.showToast('❤️ Added to favorites', 'success');
            } else {
                this.favorites.splice(index, 1);
                item.favorite = false;
                this.showToast('💔 Removed from favorites', 'info');
            }
            localStorage.setItem('favorites', JSON.stringify(this.favorites));
        },
        
        openStatsModal() {
            this.loadStats();
            this.showStatsModal = true;
        },
        
        closeStatsModal() {
            this.showStatsModal = false;
        },
        
        toggleTheme() {
            this.darkMode = !this.darkMode;
            
            if (this.darkMode) {
                document.body.classList.remove('light-theme');
                document.body.style.background = '#0A0A0A';
                document.getElementById('app').classList.remove('light-theme');
            } else {
                document.body.classList.add('light-theme');
                document.body.style.background = '#f5f5f5';
                document.getElementById('app').classList.add('light-theme');
            }
        },
        
        showToast(message, type = 'info') {
            const id = ++this.toastId;
            this.toasts.push({ id, message, type });
            
            setTimeout(() => {
                this.toasts = this.toasts.filter(t => t.id !== id);
            }, 3000);
        },

        getVideoType(path) {
            if (!path) return 'video/mp4';
            const ext = path.split('.').pop().toLowerCase();
            const types = {
                'mp4': 'video/mp4',
                'webm': 'video/webm',
                'ogg': 'video/ogg',
                'avi': 'video/x-msvideo',
                'mkv': 'video/x-matroska',
                'mov': 'video/quicktime',
                'm4v': 'video/mp4',
                'mpg': 'video/mpeg',
                'mpeg': 'video/mpeg'
            };
            return types[ext] || 'video/mp4';
        },
        
        setupKeyboardShortcuts() {
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    if (this.isFullscreen) {
                        this.toggleFullscreen();
                    }
                    this.selectedItem = null;
                    this.showAddModal = false;
                    this.showStatsModal = false;
                    if (this.showPlayer) {
                        this.closePlayer();
                    }
                }
                if (e.key === 'f' || e.key === 'F') {
                    if (this.showPlayer) {
                        this.toggleFullscreen();
                    }
                }
                if (e.ctrlKey && e.key === 'n') {
                    e.preventDefault();
                    this.openAddModal();
                }
                if (e.ctrlKey && e.key === 'f') {
                    e.preventDefault();
                    document.querySelector('.search-input')?.focus();
                }
                if (e.key === 'Delete' && this.selectedItem) {
                    this.deleteItem(this.selectedItem);
                }
                if (e.key === '+' || e.key === '=') {
                    if (this.showPlayer && !this.isFullscreen) {
                        if (e.shiftKey) {
                            this.changePlayerHeight(5);
                        } else {
                            this.changePlayerSize(5);
                        }
                    }
                }
                if (e.key === '-') {
                    if (this.showPlayer && !this.isFullscreen) {
                        if (e.shiftKey) {
                            this.changePlayerHeight(-5);
                        } else {
                            this.changePlayerSize(-5);
                        }
                    }
                }
            });
        }
    },
    
    watch: {
        searchQuery(query) {
            if (!query.trim()) {
                this.applyFilter(this.activeFilter);
            }
        }
    }
});