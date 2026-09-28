const express = require('express');
const path = require('path');
const fs = require('fs');
const cors = require('cors');
const morgan = require('morgan');

const app = express();
const PORT = 3000;

// 中间件
app.use(cors());
app.use(morgan('dev'));
app.use(express.json());

// 静态文件目录
const DOWNLOADS_DIR = path.join(__dirname, 'downloads');
const RESOURCES_DIR = path.join(__dirname, 'resources');

// 确保目录存在
[DOWNLOADS_DIR, RESOURCES_DIR].forEach(dir => {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
});

// ============================================
// API 路由
// ============================================

// 获取更新清单
app.get('/manifest.json', (req, res) => {
    const manifestPath = path.join(__dirname, 'manifest.json');
    
    // 检查文件是否存在
    if (!fs.existsSync(manifestPath)) {
        return res.status(404).json({ 
            error: 'Manifest not found',
            message: '清单文件不存在'
        });
    }
    
    // 读取并发送 JSON
    fs.readFile(manifestPath, 'utf8', (err, data) => {
        if (err) {
            console.error('读取 manifest.json 失败:', err);
            return res.status(500).json({ 
                error: 'Failed to read manifest',
                message: '读取清单文件失败'
            });
        }
        
        try {
            const manifest = JSON.parse(data);
            res.json(manifest);
        } catch (parseError) {
            console.error('解析 manifest.json 失败:', parseError);
            return res.status(500).json({ 
                error: 'Invalid JSON',
                message: '清单文件格式错误'
            });
        }
    });
});

// 下载主程序
app.get('/downloads/:filename', (req, res) => {
    const filename = req.params.filename;
    const filePath = path.join(DOWNLOADS_DIR, filename);
    
    console.log(`请求下载: ${filename}`);
    
    // 检查文件是否存在
    if (!fs.existsSync(filePath)) {
        console.error(`文件不存在: ${filePath}`);
        return res.status(404).json({ 
            error: 'File not found',
            message: `文件不存在: ${filename}`
        });
    }
    
    // 获取文件信息
    const stat = fs.statSync(filePath);
    const fileSize = stat.size;
    
    console.log(`文件大小: ${(fileSize / 1024 / 1024).toFixed(2)} MB`);
    
    // 设置响应头
    res.setHeader('Content-Type', 'application/octet-stream');
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    res.setHeader('Content-Length', fileSize);
    
    // 支持断点续传
    const range = req.headers.range;
    if (range) {
        const parts = range.replace(/bytes=/, '').split('-');
        const start = parseInt(parts[0], 10);
        const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
        const chunksize = (end - start) + 1;
        
        console.log(`断点续传: ${start}-${end}/${fileSize}`);
        
        res.status(206); // Partial Content
        res.setHeader('Content-Range', `bytes ${start}-${end}/${fileSize}`);
        res.setHeader('Content-Length', chunksize);
        
        const stream = fs.createReadStream(filePath, { start, end });
        
        stream.on('error', (error) => {
            console.error('文件流错误:', error);
            if (!res.headersSent) {
                res.status(500).json({ 
                    error: 'Stream error',
                    message: '文件流读取错误'
                });
            }
        });
        
        stream.pipe(res);
    } else {
        // 普通下载
        const stream = fs.createReadStream(filePath);
        
        stream.on('error', (error) => {
            console.error('文件流错误:', error);
            // ✅ 关键修复：检查响应头是否已发送
            if (!res.headersSent) {
                res.status(500).json({ 
                    error: 'Stream error',
                    message: '文件流读取错误'
                });
            }
        });
        
        stream.on('end', () => {
            console.log(`下载完成: ${filename}`);
        });
        
        stream.pipe(res);
    }
});

// 下载资源文件
app.get('/resources/:filename', (req, res) => {
    const filename = req.params.filename;
    const filePath = path.join(RESOURCES_DIR, filename);
    
    console.log(`请求下载资源: ${filename}`);
    
    // 检查文件是否存在
    if (!fs.existsSync(filePath)) {
        console.error(`资源文件不存在: ${filePath}`);
        return res.status(404).json({ 
            error: 'Resource not found',
            message: `资源文件不存在: ${filename}`
        });
    }
    
    // 获取文件信息
    const stat = fs.statSync(filePath);
    const fileSize = stat.size;
    
    console.log(`资源文件大小: ${(fileSize / 1024 / 1024).toFixed(2)} MB`);
    
    // 设置响应头
    res.setHeader('Content-Type', 'application/zip');
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    res.setHeader('Content-Length', fileSize);
    
    // 支持断点续传
    const range = req.headers.range;
    if (range) {
        const parts = range.replace(/bytes=/, '').split('-');
        const start = parseInt(parts[0], 10);
        const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
        const chunksize = (end - start) + 1;
        
        console.log(`资源断点续传: ${start}-${end}/${fileSize}`);
        
        res.status(206);
        res.setHeader('Content-Range', `bytes ${start}-${end}/${fileSize}`);
        res.setHeader('Content-Length', chunksize);
        
        const stream = fs.createReadStream(filePath, { start, end });
        
        stream.on('error', (error) => {
            console.error('资源文件流错误:', error);
            if (!res.headersSent) {
                res.status(500).json({ 
                    error: 'Stream error',
                    message: '资源文件流读取错误'
                });
            }
        });
        
        stream.pipe(res);
    } else {
        const stream = fs.createReadStream(filePath);
        
        stream.on('error', (error) => {
            console.error('资源文件流错误:', error);
            if (!res.headersSent) {
                res.status(500).json({ 
                    error: 'Stream error',
                    message: '资源文件流读取错误'
                });
            }
        });
        
        stream.on('end', () => {
            console.log(`资源下载完成: ${filename}`);
        });
        
        stream.pipe(res);
    }
});

// 健康检查
app.get('/health', (req, res) => {
    res.json({ 
        status: 'ok',
        timestamp: new Date().toISOString(),
        message: '服务器运行正常'
    });
});

// 根路径
app.get('/', (req, res) => {
    res.json({
        name: 'BatchAiCutter Update Server',
        version: '1.0.0',
        endpoints: {
            manifest: '/manifest.json',
            downloads: '/downloads/:filename',
            resources: '/resources/:filename',
            health: '/health'
        }
    });
});

// ============================================
// 错误处理中间件
// ============================================

// 404 处理
app.use((req, res) => {
    res.status(404).json({
        error: 'Not Found',
        message: `路径不存在: ${req.path}`,
        timestamp: new Date().toISOString()
    });
});

// 全局错误处理
app.use((err, req, res, next) => {
    console.error('服务器错误:', err);
    
    // ✅ 关键修复：检查响应头是否已发送
    if (!res.headersSent) {
        res.status(err.status || 500).json({
            error: err.name || 'Internal Server Error',
            message: err.message || '服务器内部错误',
            timestamp: new Date().toISOString()
        });
    }
});

// ============================================
// 启动服务器
// ============================================

app.listen(PORT, '0.0.0.0', () => {
    console.log('='.repeat(60));
    console.log(`✅ BatchAiCutter 更新服务器已启动`);
    console.log(`📡 监听端口: ${PORT}`);
    console.log(`🌐 访问地址: http://localhost:${PORT}`);
    console.log(`📦 下载目录: ${DOWNLOADS_DIR}`);
    console.log(`📁 资源目录: ${RESOURCES_DIR}`);
    console.log('='.repeat(60));
});

// 优雅关闭
process.on('SIGTERM', () => {
    console.log('收到 SIGTERM 信号，正在关闭服务器...');
    process.exit(0);
});

process.on('SIGINT', () => {
    console.log('\n收到 SIGINT 信号，正在关闭服务器...');
    process.exit(0);
});
