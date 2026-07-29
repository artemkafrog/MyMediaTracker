const app = new Vue({
    el: '#app',
    
    data() {
        return {
            items: [],
            filteredItems: [],
            loading: false,
            darkMode: true,
            searchQuery: '',
            activeFilter: 'all',
            statusMessage: 'Ready',
            
            currentIndex: 0,
            dragStartX: 0,
            dragCurrentX: 0,
            isDragging: false,
            swipeThreshold: 50,
            
            autoPlayEnabled: true,
            autoPlayInterval: null,
            autoPlayDelay: 15000,
            
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
            watchInterval: null,
            watchTime: {},
        };
    },
    
    computed: {
        themeIcon() {
            return this.darkMode ? '🌙' : '☀️';
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
        
        formatDuration() {
            return (minutes) => {
                if (!minutes || minutes === 0) return 'N/A';
                if (minutes < 60) return minutes + ' min';
                const hours = Math.floor(minutes / 60);
                const mins = minutes % 60;
                return hours + 'h ' + mins + 'm';
            };
        },
        
        activeIndex() {
            return this.currentIndex % this.filteredItems.length;
        },
        
        displayItems() {
            return this.filteredItems;
        },
        
        trackStyle() {
            if (this.filteredItems.length === 0) return {};
            
            const container = this.$refs.carouselContainer;
            if (!container) return {};
            
            const containerWidth = container.offsetWidth || 800;
            const cardWidth = this.getCardWidth();
            const gap = this.getGap();
            const totalWidth = cardWidth + gap;
            
            // Используем нормализованный индекс для бесконечной прокрутки
            const normalizedIndex = ((this.currentIndex % this.filteredItems.length) + this.filteredItems.length) % this.filteredItems.length;
            const offset = (containerWidth / 2) - (cardWidth / 2) - (normalizedIndex * totalWidth);
            
            let dragOffset = 0;
            if (this.isDragging) {
                dragOffset = this.dragCurrentX - this.dragStartX;
            }
            
            const finalOffset = offset + dragOffset;
            
            return {
                transform: 'translateX(' + finalOffset + 'px)',
                transition: this.isDragging ? 'none' : 'transform 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94)'
            };
        },
        
        watchedCount() {
            return this.filteredItems.filter(item => item.status === 'watched').length;
        },
        
        favoritesCount() {
            return this.filteredItems.filter(item => this.favorites.includes(item.id)).length;
        },
        
        recentlyWatched() {
            const history = this.watchHistory;
            const items = this.items.filter(item => history[item.id]);
            return items.sort((a, b) => {
                return (history[b.id]?.lastWatched || 0) - (history[a.id]?.lastWatched || 0);
            });
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
                height: this.isFullscreen ? 'calc(100vh - 100px)' : (this.playerHeight + 'vh'),
                maxHeight: this.isFullscreen ? '100%' : '80vh'
            };
        }
    },
    
    mounted() {
        this.loadItems();
        this.setupKeyboardShortcuts();
        this.startAutoPlay();
        
        if (!this.darkMode) {
            document.body.classList.add('light-theme');
            document.getElementById('app').classList.add('light-theme');
        }
        
        this.cleanWatchHistory();
        window.addEventListener('resize', this.handleResize);
    },
    
    beforeDestroy() {
        this.stopAutoPlay();
        this.stopWatchTimer();
        window.removeEventListener('resize', this.handleResize);
    },
    
    methods: {
        handleResize() {
            if (this.filteredItems.length > 0) {
                this.$forceUpdate();
            }
        },
        
        getCardWidth() {
            const container = this.$refs.carouselContainer;
            if (!container) return 320;
            
            const width = container.offsetWidth;
            if (width >= 1200) return 320;
            if (width >= 992) return 300;
            if (width >= 768) return 280;
            if (width >= 480) return 240;
            return 200;
        },
        
        getGap() {
            const container = this.$refs.carouselContainer;
            if (!container) return 20;
            
            const width = container.offsetWidth;
            if (width >= 768) return 20;
            return 10;
        },
        
        getSlideStyle(index) {
            const totalItems = this.filteredItems.length;
            if (totalItems === 0) return {};
            
            // Вычисляем циклическую разницу для бесконечной прокрутки
            let diff = index - (this.currentIndex % totalItems);
            
            // Нормализуем разницу для циклического перехода
            if (diff > totalItems / 2) {
                diff = diff - totalItems;
            } else if (diff < -totalItems / 2) {
                diff = diff + totalItems;
            }
            
            const absDiff = Math.abs(diff);
            
            if (diff === 0) {
                return {
                    transform: 'scale(1) translateX(0)',
                    opacity: 1,
                    zIndex: 10
                };
            }
            
            if (absDiff === 1) {
                const dir = diff < 0 ? -1 : 1;
                return {
                    transform: 'scale(0.85) translateX(' + (dir * 10) + 'px)',
                    opacity: 0.4,
                    zIndex: 5
                };
            }
            
            const scale = Math.max(0.7, 0.85 - (absDiff - 1) * 0.05);
            const opacity = Math.max(0.15, 0.4 - (absDiff - 1) * 0.08);
            
            return {
                transform: 'scale(' + scale + ')',
                opacity: opacity,
                zIndex: 5 - Math.min(absDiff, 5)
            };
        },
        
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
                        isUrl: item.video_path && (item.video_path.startsWith('http://') || item.video_path.startsWith('https://')),
                        has_thumbnail: item.has_thumbnail || false,
                        thumbnail_url: item.thumbnail_url || null
                    }));
                    this.applyFilter(this.activeFilter);
                    this.statusMessage = 'Loaded ' + data.items.length + ' videos';
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
        
        applyFilter(filterValue) {
            this.activeFilter = filterValue;
            
            if (filterValue === 'all') {
                this.filteredItems = [...this.items];
            } else {
                this.filteredItems = this.items.filter(
                    item => item.status === filterValue
                );
            }
            
            if (this.filteredItems.length > 0) {
                this.currentIndex = Math.floor(this.filteredItems.length / 2);
            }
            
            this.restartAutoPlay();
            
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
                    if (this.filteredItems.length > 0) {
                        this.currentIndex = Math.floor(this.filteredItems.length / 2);
                    }
                    this.restartAutoPlay();
                    this.statusMessage = 'Found ' + data.items.length + ' videos';
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
        
        toggleTheme() {
            this.darkMode = !this.darkMode;
            
            if (this.darkMode) {
                document.body.classList.remove('light-theme');
                document.getElementById('app').classList.remove('light-theme');
            } else {
                document.body.classList.add('light-theme');
                document.getElementById('app').classList.add('light-theme');
            }
        },
        
        startAutoPlay() {
            this.stopAutoPlay();
            if (!this.autoPlayEnabled) return;
            if (this.filteredItems.length < 2) return;
            
            this.autoPlayInterval = setInterval(() => {
                if (this.filteredItems.length > 1 && !this.isDragging && !this.showPlayer && !this.selectedItem) {
                    this.nextVideo();
                }
            }, this.autoPlayDelay);
        },
        
        stopAutoPlay() {
            if (this.autoPlayInterval) {
                clearInterval(this.autoPlayInterval);
                this.autoPlayInterval = null;
            }
        },
        
        restartAutoPlay() {
            this.startAutoPlay();
        },
        
        toggleAutoPlay() {
            this.autoPlayEnabled = !this.autoPlayEnabled;
            if (this.autoPlayEnabled) {
                this.startAutoPlay();
                this.showToast('Autoplay enabled', 'info');
            } else {
                this.stopAutoPlay();
                this.showToast('Autoplay disabled', 'info');
            }
        },
        
        // ===== БЕСКОНЕЧНАЯ ЗАЦИКЛЕННАЯ КАРУСЕЛЬ =====
        nextVideo() {
            if (this.filteredItems.length === 0) return;
            // Бесконечная прокрутка вправо
            this.currentIndex = this.currentIndex + 1;
            this.updateStatus();
            if (this.autoPlayEnabled) {
                this.restartAutoPlay();
            }
        },
        
        prevVideo() {
            if (this.filteredItems.length === 0) return;
            // Бесконечная прокрутка влево
            this.currentIndex = this.currentIndex - 1;
            this.updateStatus();
            if (this.autoPlayEnabled) {
                this.restartAutoPlay();
            }
        },
        
        goTo(index) {
            if (this.filteredItems.length === 0) return;
            // Нормализуем индекс для бесконечной прокрутки
            const normalizedIndex = ((index % this.filteredItems.length) + this.filteredItems.length) % this.filteredItems.length;
            const currentNormalized = ((this.currentIndex % this.filteredItems.length) + this.filteredItems.length) % this.filteredItems.length;
            
            // Вычисляем кратчайший путь
            let diff = normalizedIndex - currentNormalized;
            if (diff > this.filteredItems.length / 2) {
                diff = diff - this.filteredItems.length;
            } else if (diff < -this.filteredItems.length / 2) {
                diff = diff + this.filteredItems.length;
            }
            
            this.currentIndex = this.currentIndex + diff;
            this.updateStatus();
            if (this.autoPlayEnabled) {
                this.restartAutoPlay();
            }
        },
        
        randomVideo() {
            if (this.filteredItems.length === 0) {
                this.showToast('No videos in collection', 'info');
                return;
            }
            const randomIndex = Math.floor(Math.random() * this.filteredItems.length);
            this.goTo(randomIndex);
            this.showToast('Random selection', 'info');
        },
        
        updateStatus() {
            const normalizedIndex = ((this.currentIndex % this.filteredItems.length) + this.filteredItems.length) % this.filteredItems.length;
            const item = this.filteredItems[normalizedIndex];
            if (item) {
                this.statusMessage = 'Now playing: ' + item.title;
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
        
        cleanWatchHistory() {
            const thirtyDaysAgo = Date.now() - (30 * 24 * 60 * 60 * 1000);
            let cleaned = false;
            for (const id in this.watchHistory) {
                if (this.watchHistory[id].lastWatched < thirtyDaysAgo) {
                    delete this.watchHistory[id];
                    cleaned = true;
                }
            }
            if (cleaned) {
                localStorage.setItem('watchHistory', JSON.stringify(this.watchHistory));
            }
        },
        
        openVideo(item) {
            this.selectedItem = { ...item };
            if (this.autoPlayEnabled) {
                this.stopAutoPlay();
            }
        },
        
        closeDetail() {
            this.selectedItem = null;
            if (this.autoPlayEnabled) {
                this.restartAutoPlay();
            }
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
            
            if (this.autoPlayEnabled) {
                this.stopAutoPlay();
            }
        },
        
        closePlayer() {
            this.showPlayer = false;
            this.currentVideo = null;
            this.isFullscreen = false;
            this.stopWatchTimer();
            if (this.$refs.videoPlayer) {
                this.$refs.videoPlayer.pause();
            }
            if (this.autoPlayEnabled) {
                this.restartAutoPlay();
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
            this.showToast('Playback finished', 'info');
            if (this.currentVideo) {
                this.updateWatchTime(this.currentVideo.id, 100);
            }
            this.stopWatchTimer();
            if (this.autoPlayEnabled) {
                this.restartAutoPlay();
            }
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
                
        startDrag(event) {
            if (this.filteredItems.length < 2) return;
            this.isDragging = true;
            this.dragStartX = event.clientX;
            this.dragCurrentX = event.clientX;
            if (this.autoPlayEnabled) {
                this.stopAutoPlay();
            }
        },
        
        onDrag(event) {
            if (!this.isDragging) return;
            this.dragCurrentX = event.clientX;
        },
        
        endDrag() {
            if (!this.isDragging) return;
            this.isDragging = false;
            
            const deltaX = this.dragCurrentX - this.dragStartX;
            if (Math.abs(deltaX) > this.swipeThreshold) {
                if (deltaX < 0) {
                    this.nextVideo();
                } else {
                    this.prevVideo();
                }
            }
            if (this.autoPlayEnabled) {
                this.restartAutoPlay();
            }
        },
        
        startTouch(event) {
            if (this.filteredItems.length < 2) return;
            const touch = event.touches[0];
            this.isDragging = true;
            this.dragStartX = touch.clientX;
            this.dragCurrentX = touch.clientX;
            if (this.autoPlayEnabled) {
                this.stopAutoPlay();
            }
        },
        
        onTouch(event) {
            if (!this.isDragging) return;
            const touch = event.touches[0];
            this.dragCurrentX = touch.clientX;
        },
        
        endTouch() {
            if (!this.isDragging) return;
            this.isDragging = false;
            
            const deltaX = this.dragCurrentX - this.dragStartX;
            if (Math.abs(deltaX) > this.swipeThreshold) {
                if (deltaX < 0) {
                    this.nextVideo();
                } else {
                    this.prevVideo();
                }
            }
            if (this.autoPlayEnabled) {
                this.restartAutoPlay();
            }
        },
        
        openAddModal() {
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
            if (this.autoPlayEnabled) {
                this.stopAutoPlay();
            }
        },
        
        closeAddModal() {
            this.showAddModal = false;
            if (this.autoPlayEnabled) {
                this.restartAutoPlay();
            }
        },
        
        async addItem() {
            if (!this.newItem.title.trim()) {
                const now = new Date();
                this.newItem.title = 'Video from ' + now.toLocaleDateString('en-US') + ' ' + now.toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit'});
            }
            
            let videoPath = this.newItem.video_path;
            if (this.newItem.video_url && this.newItem.video_url.trim()) {
                videoPath = this.newItem.video_url.trim();
            }
            
            if (!videoPath) {
                this.showToast('Specify video link or upload file', 'error');
                return;
            }
            
            this.loading = true;
            
            try {
                const response = await fetch('/api/items', {
                    method: 'POST',
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
                    this.items.push({ 
                        ...data.item, 
                        favorite: false,
                        isUrl: videoPath.startsWith('http://') || videoPath.startsWith('https://')
                    });
                    this.applyFilter(this.activeFilter);
                    this.closeAddModal();
                    this.showToast(data.message, 'success');
                    this.statusMessage = 'Item added';
                } else {
                    this.showToast(data.error || 'Add error', 'error');
                }
            } catch (error) {
                console.error('Error adding item:', error);
                this.showToast('Error adding item', 'error');
            } finally {
                this.loading = false;
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
                    this.showToast(data.message, 'success');
                } else {
                    this.showToast(data.error || 'Upload error', 'error');
                }
            } catch (error) {
                console.error('Error uploading video:', error);
                this.showToast('Video upload error', 'error');
            }
            
            event.target.value = '';
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
                    this.showToast(data.message, 'success');
                } else {
                    this.showToast(data.error || 'Delete error', 'error');
                }
            } catch (error) {
                console.error('Error deleting item:', error);
                this.showToast('Delete error', 'error');
            }
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
        
        showToast(message, type = 'info') {
            const id = ++this.toastId;
            this.toasts.push({ id, message, type });
            
            setTimeout(() => {
                this.toasts = this.toasts.filter(t => t.id !== id);
            }, 3000);
        },
        
        setupKeyboardShortcuts() {
            document.addEventListener('keydown', (e) => {
                if (e.key === 'ArrowRight') {
                    e.preventDefault();
                    this.nextVideo();
                }
                if (e.key === 'ArrowLeft') {
                    e.preventDefault();
                    this.prevVideo();
                }
                if (e.key === 'Enter') {
                    if (this.filteredItems.length > 0 && !this.selectedItem && !this.showPlayer) {
                        e.preventDefault();
                        const normalizedIndex = ((this.currentIndex % this.filteredItems.length) + this.filteredItems.length) % this.filteredItems.length;
                        const currentItem = this.filteredItems[normalizedIndex];
                        if (currentItem) {
                            this.openVideo(currentItem);
                        }
                    }
                }
                if (e.key === ' ' && this.selectedItem) {
                    e.preventDefault();
                    this.playVideo(this.selectedItem);
                }
                if (e.key === 'Escape') {
                    if (this.isFullscreen) {
                        this.toggleFullscreen();
                    }
                    this.selectedItem = null;
                    this.showAddModal = false;
                    if (this.showPlayer) {
                        this.closePlayer();
                    }
                    if (this.autoPlayEnabled) {
                        this.restartAutoPlay();
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
                if (e.key === 'r' && !e.ctrlKey && !e.metaKey) {
                    this.randomVideo();
                }
                if (e.key === 'a' && !e.ctrlKey && !e.metaKey) {
                    this.toggleAutoPlay();
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
        },
    },
    
    watch: {
        searchQuery(query) {
            if (!query.trim()) {
                this.applyFilter(this.activeFilter);
            }
        },
        
        filteredItems() {
            if (this.autoPlayEnabled) {
                this.restartAutoPlay();
            }
        }
    }
});