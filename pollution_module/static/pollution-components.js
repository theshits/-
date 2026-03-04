/**
 * 污染扩散可视化组件
 * ==================
 * 
 * 可嵌入任何网页的独立组件
 * 依赖: Leaflet, ECharts (CDN加载)
 * 
 * 使用示例:
 * <div id="pollution-map"></div>
 * <script src="pollution-components.js"></script>
 * <script>
 *   const viz = new PollutionVisualization({
 *     container: 'pollution-map',
 *     apiBase: '/api/pollution'
 *   });
 *   
 *   viz.runSimulation(sources, receptors, meteorology);
 * </script>
 */

class PollutionVisualization {
    /**
     * 初始化污染扩散可视化组件
     * @param {Object} options 配置选项
     * @param {string} options.container 地图容器ID
     * @param {string} options.apiBase API基础路径
     * @param {Object} options.center 地图中心 {lat, lon}
     * @param {number} options.zoom 初始缩放级别
     */
    constructor(options) {
        this.container = options.container || 'map';
        this.apiBase = options.apiBase || '/api/pollution';
        this.center = options.center || { lat: 39.9, lon: 116.4 };
        this.zoom = options.zoom || 11;
        
        this.map = null;
        this.sourceMarkers = [];
        this.receptorMarkers = [];
        this.plumeLayer = null;
        
        this.sourceColor = options.sourceColor || '#FF5722';
        this.receptorColor = options.receptorColor || '#2196F3';
        
        this._initMap();
    }
    
    _initMap() {
        this.map = L.map(this.container).setView(
            [this.center.lat, this.center.lon], 
            this.zoom
        );
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);
    }
    
    /**
     * 添加排放源标记
     * @param {Array} sources 排放源列表
     */
    addSources(sources) {
        this._clearMarkers('source');
        
        sources.forEach(source => {
            const marker = L.circleMarker([source.lat, source.lon], {
                radius: 10,
                fillColor: source.color || this.sourceColor,
                color: '#fff',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.8
            });
            
            marker.bindPopup(`
                <b>${source.name || '排放源'}</b><br>
                排放速率: ${source.emission_rate} g/s<br>
                高度: ${source.height} m
            `);
            
            marker.addTo(this.map);
            this.sourceMarkers.push(marker);
        });
    }
    
    /**
     * 添加受体点标记
     * @param {Array} receptors 受体点列表
     */
    addReceptors(receptors) {
        this._clearMarkers('receptor');
        
        receptors.forEach(receptor => {
            const marker = L.marker([receptor.lat, receptor.lon], {
                icon: L.divIcon({
                    html: `<div style="
                        background: ${receptor.color || this.receptorColor};
                        width: 16px;
                        height: 16px;
                        border: 2px solid white;
                        border-radius: 3px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                    "></div>`,
                    className: 'receptor-marker',
                    iconSize: [16, 16],
                    iconAnchor: [8, 8]
                })
            });
            
            marker.bindPopup(`<b>${receptor.name || '受体点'}</b>`);
            marker.addTo(this.map);
            this.receptorMarkers.push(marker);
        });
    }
    
    _clearMarkers(type) {
        const markers = type === 'source' ? this.sourceMarkers : this.receptorMarkers;
        markers.forEach(m => this.map.removeLayer(m));
        
        if (type === 'source') {
            this.sourceMarkers = [];
        } else {
            this.receptorMarkers = [];
        }
    }
    
    /**
     * 运行扩散模拟
     * @param {Array} sources 排放源列表
     * @param {Array} receptors 受体点列表
     * @param {Object} meteorology 气象条件
     * @returns {Promise<Object>} 模拟结果
     */
    async runSimulation(sources, receptors, meteorology) {
        try {
            const response = await fetch(`${this.apiBase}/simulate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sources: sources,
                    receptors: receptors,
                    meteorology: meteorology
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.addSources(sources);
                this.addReceptors(receptors);
                this._visualizePlume(result.data);
                return result.data;
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('模拟失败:', error);
            throw error;
        }
    }
    
    _visualizePlume(data) {
        if (this.plumeLayer) {
            this.map.removeLayer(this.plumeLayer);
        }
        
        const { concentrations, lat_grid, lon_grid } = data;
        const maxConc = Math.max(...concentrations.flat());
        
        if (maxConc === 0) return;
        
        const colors = ['#E3F2FD', '#90CAF9', '#42A5F5', '#1E88E5', '#1565C0', '#0D47A1'];
        const levels = [0.1, 0.2, 0.3, 0.5, 0.7, 0.9];
        
        const layers = [];
        
        for (let i = levels.length - 1; i >= 0; i--) {
            const threshold = levels[i] * maxConc;
            const points = [];
            
            for (let lat = 0; lat < lat_grid.length; lat++) {
                for (let lon = 0; lon < lon_grid.length; lon++) {
                    if (concentrations[lat][lon] >= threshold) {
                        points.push([lat_grid[lat], lon_grid[lon]]);
                    }
                }
            }
            
            if (points.length > 2) {
                const polygon = L.polygon(points, {
                    color: colors[i],
                    fillColor: colors[i],
                    fillOpacity: 0.3,
                    weight: 1
                });
                layers.push(polygon);
            }
        }
        
        this.plumeLayer = L.layerGroup(layers);
        this.plumeLayer.addTo(this.map);
    }
    
    /**
     * 清除扩散云图
     */
    clearPlume() {
        if (this.plumeLayer) {
            this.map.removeLayer(this.plumeLayer);
            this.plumeLayer = null;
        }
    }
    
    /**
     * 适配地图视图
     */
    fitBounds() {
        const bounds = [];
        
        this.sourceMarkers.forEach(m => bounds.push(m.getLatLng()));
        this.receptorMarkers.forEach(m => bounds.push(m.getLatLng()));
        
        if (bounds.length > 0) {
            this.map.fitBounds(bounds, { padding: [50, 50] });
        }
    }
}


/**
 * 风向雷达控件
 * ============
 * 
 * 可拖动的雷达状风向风速选择器
 * 
 * 使用示例:
 * <canvas id="wind-rose" width="200" height="200"></canvas>
 * <script>
 *   const windRose = new WindRoseControl('wind-rose', {
 *     direction: 0,
 *     speed: 2,
 *     onChange: (dir, speed) => console.log(dir, speed)
 *   });
 * </script>
 */
class WindRoseControl {
    /**
     * 初始化风向雷达控件
     * @param {string} canvasId Canvas元素ID
     * @param {Object} options 配置选项
     */
    constructor(canvasId, options = {}) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        
        this.direction = options.direction || 0;
        this.speed = options.speed || 2;
        this.maxSpeed = options.maxSpeed || 20;
        this.onChange = options.onChange || (() => {});
        
        this.radius = Math.min(this.canvas.width, this.canvas.height) / 2 - 20;
        this.centerX = this.canvas.width / 2;
        this.centerY = this.canvas.height / 2;
        
        this._bindEvents();
        this.draw();
    }
    
    _bindEvents() {
        let isDragging = false;
        
        const updateFromMouse = (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const x = e.clientX - rect.left - this.centerX;
            const y = this.centerY - (e.clientY - rect.top);
            
            this.direction = Math.round(Math.atan2(x, y) * 180 / Math.PI + 360) % 360;
            this.speed = Math.min(this.maxSpeed, Math.max(0.5, Math.sqrt(x*x + y*y) / this.radius * this.maxSpeed));
            
            this.draw();
            this.onChange(this.direction, this.speed);
        };
        
        this.canvas.addEventListener('mousedown', (e) => {
            isDragging = true;
            updateFromMouse(e);
        });
        
        this.canvas.addEventListener('mousemove', (e) => {
            if (isDragging) {
                updateFromMouse(e);
            }
        });
        
        this.canvas.addEventListener('mouseup', () => {
            isDragging = false;
        });
        
        this.canvas.addEventListener('mouseleave', () => {
            isDragging = false;
        });
    }
    
    /**
     * 绘制雷达图
     */
    draw() {
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        ctx.strokeStyle = '#ddd';
        ctx.lineWidth = 1;
        
        for (let i = 0; i < 8; i++) {
            const angle = i * Math.PI / 4;
            ctx.beginPath();
            ctx.moveTo(this.centerX, this.centerY);
            ctx.lineTo(
                this.centerX + this.radius * Math.sin(angle),
                this.centerY - this.radius * Math.cos(angle)
            );
            ctx.stroke();
        }
        
        for (let i = 1; i <= 4; i++) {
            ctx.beginPath();
            ctx.arc(this.centerX, this.centerY, this.radius * i / 4, 0, Math.PI * 2);
            ctx.stroke();
        }
        
        const labels = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
        ctx.fillStyle = '#666';
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'center';
        
        labels.forEach((label, i) => {
            const angle = i * Math.PI / 4;
            const x = this.centerX + (this.radius + 15) * Math.sin(angle);
            const y = this.centerY - (this.radius + 15) * Math.cos(angle) + 4;
            ctx.fillText(label, x, y);
        });
        
        const angle = (90 - this.direction) * Math.PI / 180;
        const len = this.speed / this.maxSpeed * this.radius;
        
        ctx.strokeStyle = '#007AFF';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(this.centerX, this.centerY);
        ctx.lineTo(
            this.centerX + len * Math.cos(angle),
            this.centerY - len * Math.sin(angle)
        );
        ctx.stroke();
        
        ctx.beginPath();
        ctx.arc(this.centerX, this.centerY, 6, 0, Math.PI * 2);
        ctx.fillStyle = '#007AFF';
        ctx.fill();
    }
    
    /**
     * 设置风向
     * @param {number} direction 风向（度）
     */
    setDirection(direction) {
        this.direction = direction % 360;
        this.draw();
        this.onChange(this.direction, this.speed);
    }
    
    /**
     * 设置风速
     * @param {number} speed 风速
     */
    setSpeed(speed) {
        this.speed = Math.min(this.maxSpeed, Math.max(0.1, speed));
        this.draw();
        this.onChange(this.direction, this.speed);
    }
    
    /**
     * 获取当前值
     * @returns {Object} {direction, speed}
     */
    getValue() {
        return {
            direction: this.direction,
            speed: this.speed
        };
    }
}


/**
 * 贡献度图表组件
 * ==============
 * 
 * 显示污染源贡献度排名图表
 * 
 * 使用示例:
 * <div id="contribution-chart"></div>
 * <script>
 *   const chart = new ContributionChart('contribution-chart');
 *   chart.setData(contributions);
 * </script>
 */
class ContributionChart {
    /**
     * 初始化贡献度图表
     * @param {string} containerId 容器ID
     * @param {Object} options 配置选项
     */
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            width: options.width || '100%',
            height: options.height || '300px',
            ...options
        };
        
        this.container.style.width = this.options.width;
        this.container.style.height = this.options.height;
        
        if (typeof echarts !== 'undefined') {
            this.chart = echarts.init(this.container);
        }
    }
    
    /**
     * 设置数据并渲染
     * @param {Array} contributions 贡献度数据
     */
    setData(contributions) {
        if (!this.chart) {
            this._renderSimple(contributions);
            return;
        }
        
        const sorted = [...contributions].sort((a, b) => b.percentage - a.percentage);
        
        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' }
            },
            grid: {
                left: '3%',
                right: '10%',
                top: '3%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: {
                type: 'value',
                max: 100,
                axisLabel: { formatter: '{value}%' }
            },
            yAxis: {
                type: 'category',
                data: sorted.map(c => c.source_name).reverse()
            },
            series: [{
                type: 'bar',
                data: sorted.map(c => c.percentage).reverse(),
                itemStyle: {
                    color: {
                        type: 'linear',
                        x: 0, y: 0, x2: 1, y2: 0,
                        colorStops: [
                            { offset: 0, color: '#007AFF' },
                            { offset: 1, color: '#5AC8FA' }
                        ]
                    },
                    borderRadius: [0, 4, 4, 0]
                },
                label: {
                    show: true,
                    position: 'right',
                    formatter: '{c}%'
                }
            }]
        };
        
        this.chart.setOption(option);
    }
    
    _renderSimple(contributions) {
        const sorted = [...contributions].sort((a, b) => b.percentage - a.percentage);
        const maxPct = Math.max(...sorted.map(c => c.percentage));
        
        let html = '<div style="font-family: sans-serif;">';
        
        sorted.forEach(c => {
            html += `
                <div style="display: flex; align-items: center; margin: 8px 0;">
                    <span style="width: 100px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        ${c.source_name}
                    </span>
                    <div style="flex: 1; height: 8px; background: #f0f0f0; border-radius: 4px; margin: 0 10px;">
                        <div style="width: ${c.percentage/maxPct*100}%; height: 100%; background: #007AFF; border-radius: 4px;"></div>
                    </div>
                    <span style="width: 50px; text-align: right;">${c.percentage.toFixed(1)}%</span>
                </div>
            `;
        });
        
        html += '</div>';
        this.container.innerHTML = html;
    }
    
    /**
     * 调整图表大小
     */
    resize() {
        if (this.chart) {
            this.chart.resize();
        }
    }
}


// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        PollutionVisualization,
        WindRoseControl,
        ContributionChart
    };
}
