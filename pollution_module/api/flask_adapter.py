"""
Flask适配器
==========

将污染扩散模块集成到Flask应用

使用示例:
    from flask import Flask
    from pollution_module.api import create_flask_blueprint
    
    app = Flask(__name__)
    app.register_blueprint(create_flask_blueprint(), url_prefix='/api/pollution')
"""

from typing import Dict, Any
from flask import Blueprint, request, jsonify

from .common import run_simulation_api, get_contribution_api, calculate_single_point_api


def create_blueprint() -> Blueprint:
    """
    创建Flask蓝图
    
    Returns:
        Blueprint实例
    """
    bp = Blueprint('pollution', __name__, url_prefix='')
    
    @bp.route('/simulate', methods=['POST'])
    def simulate():
        """
        运行扩散模拟
        """
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': '请求数据不能为空'}), 400
        
        sources = data.get('sources', [])
        receptors = data.get('receptors', [])
        meteorology = data.get('meteorology', {})
        grid_size = data.get('grid_size', 50)
        domain_radius = data.get('domain_radius', 5000)
        
        result = run_simulation_api(
            sources=sources,
            receptors=receptors,
            meteorology=meteorology,
            grid_size=grid_size,
            domain_radius=domain_radius
        )
        
        if not result['success']:
            return jsonify(result), 400
        
        return jsonify(result)
    
    @bp.route('/single-point', methods=['POST'])
    def single_point():
        """
        计算单点浓度
        """
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': '请求数据不能为空'}), 400
        
        result = calculate_single_point_api(
            source=data.get('source', {}),
            receptor=data.get('receptor', {}),
            meteorology=data.get('meteorology', {})
        )
        
        if not result['success']:
            return jsonify(result), 400
        
        return jsonify(result)
    
    @bp.route('/contributions', methods=['POST'])
    def contributions():
        """
        计算贡献度排名
        """
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': '请求数据不能为空'}), 400
        
        result = get_contribution_api(
            source_concentrations=data.get('source_concentrations', {}),
            receptor_name=data.get('receptor_name', '')
        )
        
        if not result['success']:
            return jsonify(result), 400
        
        return jsonify(result)
    
    @bp.route('/stability-classes', methods=['GET'])
    def stability_classes():
        """
        获取稳定度等级说明
        """
        from ..gaussian_plume import StabilityClassifier
        
        classes = {}
        for cls in ['A', 'B', 'C', 'D', 'E', 'F']:
            classes[cls] = StabilityClassifier.get_description(cls)
        
        return jsonify({
            'success': True,
            'data': classes
        })
    
    @bp.route('/health', methods=['GET'])
    def health():
        """健康检查"""
        return jsonify({'status': 'healthy', 'module': 'pollution_module'})
    
    return bp
