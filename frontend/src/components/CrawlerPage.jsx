import React, { useState, useEffect, useCallback } from 'react';
import { Modal, Form, Input, message } from 'antd';
import { PlusOutlined, PlayCircleOutlined, StopOutlined, DeleteOutlined, LoadingOutlined } from '@ant-design/icons';

function CrawlerPage() {
  const [crawlers, setCrawlers] = useState([]);
  const [instances, setInstances] = useState({});
  const [crawlerStatus, setCrawlerStatus] = useState({
    is_running: false,
    completed: false,
    running_instances: []
  });
  const [progressData, setProgressData] = useState({});
  const [currentCrawler, setCurrentCrawler] = useState(null);
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  // 获取爬虫列表
  const fetchCrawlers = useCallback(async () => {
    try {
      const response = await fetch('/api/crawlers');
      const data = await response.json();
      setCrawlers(data.crawlers || []);
    } catch (error) {
      console.error('获取爬虫列表失败:', error);
    }
  }, []);

  // 获取爬虫实例
  const fetchInstances = useCallback(async (crawlerName) => {
    try {
      const response = await fetch(`/api/crawler-instances?name=${crawlerName}`);
      const data = await response.json();
      setInstances(prev => ({
        ...prev,
        [crawlerName]: data.instances || []
      }));
    } catch (error) {
      console.error(`获取${crawlerName}的实例失败:`, error);
    }
  }, []);



  // 创建爬虫实例
  const createCrawlerInstance = async (values) => {
    if (!currentCrawler) return;
    
    setLoading(true);
    try {
      const keywords = values.keywords.split(',').map(k => k.trim()).filter(k => k);

      const response = await fetch('/api/create-crawler-instance', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: currentCrawler,
          instance_name: values.instance_name,
          keywords: keywords,
          description: values.description.trim()
        })
      });

      const result = await response.json();
      if (result.success) {
        message.success(result.message);
        fetchInstances(currentCrawler);
        Modal.destroyAll();
      } else {
        message.error('创建实例失败: ' + result.error);
      }
    } catch (error) {
      message.error('创建实例失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // 启动爬虫实例
  const startCrawlerInstance = async (crawlerName, instanceName) => {
    Modal.confirm({
      title: '确认启动',
      content: `确定要启动实例 ${instanceName} 吗？`,
      onOk: async () => {
        try {
          const response = await fetch('/api/start-crawler-instance', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              name: crawlerName,
              instance_name: instanceName
            })
          });

          const result = await response.json();
          if (result.success) {
            message.success(result.message);
            fetchInstances(crawlerName);
          } else {
            message.error('启动实例失败: ' + result.error);
          }
        } catch (error) {
          message.error('启动实例失败: ' + error.message);
        }
      }
    });
  };

  // 停止爬虫实例
  const stopCrawlerInstance = async (crawlerName, instanceId) => {
    Modal.confirm({
      title: '确认停止',
      content: '确定要停止这个爬虫实例吗？',
      onOk: async () => {
        try {
          const response = await fetch('/api/stop-crawler-instance', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              name: crawlerName,
              instance_id: instanceId
            })
          });

          const result = await response.json();
          if (result.success) {
            message.success(result.message);
            fetchInstances(crawlerName);
          } else {
            message.error('停止实例失败: ' + result.error);
          }
        } catch (error) {
          message.error('停止实例失败: ' + error.message);
        }
      }
    });
  };

  // 删除爬虫实例
  const deleteCrawlerInstance = async (crawlerName, instanceName) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除实例 ${instanceName} 吗？此操作不可恢复。`,
      onOk: async () => {
        try {
          const response = await fetch('/api/delete-crawler-instance', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              name: crawlerName,
              instance_name: instanceName
            })
          });

          const result = await response.json();
          if (result.success) {
            message.success(result.message);
            fetchInstances(crawlerName);
          } else {
            message.error('删除实例失败: ' + result.error);
          }
        } catch (error) {
          message.error('删除实例失败: ' + error.message);
        }
      }
    });
  };

  // 获取实例的进度信息
  const getInstanceProgress = (crawlerName, instanceId) => {
    const crawlerProgress = Array.isArray(progressData[crawlerName]) ? progressData[crawlerName] : [];
    return crawlerProgress.find(p => p.instance_id === instanceId) || null;
  };

  useEffect(() => {
    fetchCrawlers();
  }, [fetchCrawlers]);

  useEffect(() => {
    crawlers.forEach(crawler => {
      fetchInstances(crawler.name);
    });
  }, [crawlers, fetchInstances]);

  useEffect(() => {
    // 使用SSE替代轮询
    const eventSource = new EventSource('/api/sse');
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.status) {
          setCrawlerStatus(data.status);
        }
        if (data.progress) {
          setProgressData(data.progress);
        }
      } catch (error) {
        console.error('解析SSE消息失败:', error);
      }
    };
    
    eventSource.onerror = (error) => {
      console.error('SSE连接错误:', error);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, []);

  return (
    <div className="page">
      <div className="control-section">
        <div
          className={`status ${crawlerStatus.is_running ? 'running' : crawlerStatus.completed ? 'success' : ''}`}
        >
          {crawlerStatus.is_running ? (
            <>
              <LoadingOutlined style={{ marginRight: '8px' }} />
              状态：运行中 {crawlerStatus.running_instances.length} 个实例
            </>
          ) : crawlerStatus.completed ? (
            <>
              <span style={{ marginRight: '8px' }}>✓</span>
              状态：已完成
            </>
          ) : (
            <>
              <span style={{ marginRight: '8px' }}>⏱</span>
              状态：等待
            </>
          )}
        </div>
      </div>

      <div className="section">
        <h2>爬虫列表</h2>
        <div className="crawler-list">
          {crawlers.length > 0 ? (
            crawlers.map(crawler => (
              <div key={crawler.name} className="crawler-item" data-name={crawler.name}>
                <div className="crawler-name">
                  <i className="fas fa-spider"></i>
                  {crawler.name}
                </div>
                <div className="crawler-controls">
                  <button
                    className="crawler-btn start"
                    onClick={() => {
                      setCurrentCrawler(crawler.name);
                      form.resetFields();
                      Modal.info({
                        title: '创建爬虫实例',
                        content: (
                          <Form
                            form={form}
                            layout="vertical"
                            onFinish={createCrawlerInstance}
                          >
                            <Form.Item
                              name="instance_name"
                              label="实例名称"
                              rules={[{ required: true, message: '请输入实例名称' }]}
                            >
                              <Input placeholder="请输入实例名称" />
                            </Form.Item>
                            <Form.Item
                              name="keywords"
                              label="搜索关键字"
                              rules={[{ required: true, message: '请输入搜索关键字' }]}
                            >
                              <Input placeholder="多个关键字用逗号分隔" />
                            </Form.Item>
                            <Form.Item
                              name="description"
                              label="实例描述（可选）"
                            >
                              <Input.TextArea rows={4} placeholder="请输入实例描述" />
                            </Form.Item>
                          </Form>
                        ),
                        footer: [
                          <button key="cancel" className="btn cancel" onClick={() => Modal.destroyAll()}>
                            取消
                          </button>,
                          <button
                            key="submit"
                            className="btn"
                            onClick={() => form.submit()}
                            disabled={loading}
                          >
                            {loading ? <LoadingOutlined spin /> : '创建'}
                          </button>,
                        ],
                      });
                    }}
                    title="创建爬虫实例"
                  >
                    <PlusOutlined />
                  </button>
                </div>
                <div className="crawler-instances">
                  <h4>
                    <i className="fas fa-cubes"></i>
                    实例列表
                  </h4>
                  <div className="instance-list">
                    {instances[crawler.name] && instances[crawler.name].length > 0 ? (
                      instances[crawler.name].map(instance => {
                        const progress = getInstanceProgress(crawler.name, instance.id);
                        return (
                          <div key={instance.id} className="instance-item" data-instance-id={instance.id}>
                            <div className="instance-header">
                              <div className="instance-name">{instance.instance_name}</div>
                              <div className="instance-actions">
                                {!crawlerStatus.running_instances.includes(instance.id) ? (
                                  <button
                                    className="crawler-btn start"
                                    onClick={() => startCrawlerInstance(crawler.name, instance.instance_name)}
                                    title="启动"
                                  >
                                    <PlayCircleOutlined />
                                  </button>
                                ) : (
                                  <button
                                    className="crawler-btn stop"
                                    onClick={() => stopCrawlerInstance(crawler.name, instance.id)}
                                    title="停止"
                                  >
                                    <StopOutlined />
                                  </button>
                                )}
                                <button
                                  className="crawler-btn delete"
                                  onClick={() => deleteCrawlerInstance(crawler.name, instance.instance_name)}
                                  title="删除"
                                >
                                  <DeleteOutlined />
                                </button>
                              </div>
                            </div>
                            {instance.keywords && (
                              <div className="instance-keywords">
                                <i className="fas fa-tags"></i>
                                关键字: {instance.keywords.join(', ')}
                              </div>
                            )}
                            {instance.description && (
                              <div className="instance-description">
                                <i className="fas fa-comment"></i>
                                描述: {instance.description}
                              </div>
                            )}
                            {crawlerStatus.running_instances.includes(instance.id) && (
                              <div className="crawler-progress">
                                <div className="progress-bar-container">
                                  <div
                                    className="progress-bar"
                                    style={{ width: `${progress?.progress || 0}%` }}
                                  ></div>
                                </div>
                                <div className="progress-details">
                                  <div className="progress-text">
                                    {Math.round(progress?.progress || 0)}%
                                  </div>
                                  <div className="progress-stats">
                                    {progress?.current || 0}/{progress?.total || 0}
                                  </div>
                                  {progress?.message && (
                                    <div className="progress-message">
                                      {progress.message}
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })
                    ) : (
                      <div className="no-instances">暂无实例</div>
                    )}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="status">暂无可用爬虫</div>
          )}
        </div>
      </div>
    </div>
  );
}

export default CrawlerPage;
