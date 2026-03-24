import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Modal, message } from 'antd';
import { ReloadOutlined, DeleteOutlined, AppstoreOutlined, TableOutlined } from '@ant-design/icons';

const DataPage = React.memo(() => {
  const [items, setItems] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [displayMode, setDisplayMode] = useState('card'); // 'card' or 'table'
  const [selectedItem, setSelectedItem] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const isLoadingRef = useRef(false);

  // 加载数据
  const loadData = useCallback(async (page = 1) => {
    if (isLoadingRef.current) return; // 使用ref防止重复请求
    isLoadingRef.current = true;
    setLoading(true);
    try {
      const response = await fetch(`/api/items?page=${page}&limit=12`);
      const data = await response.json();
      setItems(data.items || []);
      setCurrentPage(data.page);
      setTotalPages(data.total_pages || 1);
    } catch (error) {
      console.error('加载数据失败:', error);
      message.error('加载数据失败');
      setItems([]);
    } finally {
      setLoading(false);
      isLoadingRef.current = false;
    }
  }, []);

  // 清除数据
  const clearData = useCallback(() => {
    Modal.confirm({
      title: '确认清除',
      content: '确定要清除所有数据吗？此操作不可恢复！',
      onOk: async () => {
        try {
          const response = await fetch('/api/clear-data', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            }
          });

          const result = await response.json();
          if (result.success) {
            message.success(result.message);
            loadData(1);
          } else {
            message.error('清除数据失败: ' + result.error);
          }
        } catch (error) {
          message.error('清除数据失败: ' + error.message);
        }
      }
    });
  }, [loadData]);

  // 分页导航
  const handlePageChange = useCallback((page) => {
    if (page >= 1 && page <= totalPages) {
      loadData(page);
    }
  }, [loadData, totalPages]);

  // 处理双击事件
  const handleDoubleClick = useCallback((item) => {
    setSelectedItem(item);
    setShowModal(true);
  }, []);

  // 关闭弹窗
  const closeModal = useCallback(() => {
    setShowModal(false);
    setSelectedItem(null);
  }, []);

  // 生成分页链接
  const renderPagination = useCallback(() => {
    const pages = [];
    const maxVisible = 5;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);
    
    if (end - start < maxVisible - 1) {
      start = Math.max(1, end - maxVisible + 1);
    }

    // 上一页
    if (currentPage > 1) {
      pages.push(
        <a
          key="prev"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            handlePageChange(currentPage - 1);
          }}
        >
          上一页
        </a>
      );
    }

    // 页码
    for (let i = start; i <= end; i++) {
      pages.push(
        <a
          key={i}
          href="#"
          className={i === currentPage ? 'active' : ''}
          onClick={(e) => {
            e.preventDefault();
            handlePageChange(i);
          }}
        >
          {i}
        </a>
      );
    }

    // 下一页
    if (currentPage < totalPages) {
      pages.push(
        <a
          key="next"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            handlePageChange(currentPage + 1);
          }}
        >
          下一页
        </a>
      );
    }

    return pages;
  }, [currentPage, totalPages, handlePageChange]);

  useEffect(() => {
    loadData(1);
  }, [loadData]);

  return (
    <div className="page">
      <div className="control-section">
        <button
          id="refreshData"
          className="btn"
          onClick={() => loadData(currentPage)}
          title="刷新数据"
          disabled={loading}
        >
          <ReloadOutlined />
        </button>
        <div className="right-controls">
          <button
            id="clearData"
            className="btn danger"
            onClick={clearData}
            title="清除所有数据"
            disabled={loading}
          >
            <DeleteOutlined />
          </button>
          <div className="display-mode-toggle">
            <button
              className={`mode-btn ${displayMode === 'card' ? 'active' : ''}`}
              onClick={() => setDisplayMode('card')}
              title="卡片模式"
            >
              <AppstoreOutlined />
            </button>
            <button
              className={`mode-btn ${displayMode === 'table' ? 'active' : ''}`}
              onClick={() => setDisplayMode('table')}
              title="表格模式"
            >
              <TableOutlined />
            </button>
          </div>
        </div>
      </div>

      <div id="dataContainer">
        {loading ? (
          <div className="status">正在加载数据...</div>
        ) : items.length > 0 ? (
          <>
            {displayMode === 'card' ? (
              <div className="item-grid">
                {items.map((item) => (
                  <div key={item.id || item.item_id} className="item-card" data-item-id={item.id || item.item_id}>
                    <div className="item-carousel">
                      <div className="carousel-container">
                        <div className="carousel-track" style={{ transform: `translateX(-${0 * 100}%)` }}>
                          {item.detail_data && item.detail_data.photos && Array.isArray(item.detail_data.photos) ? (
                            item.detail_data.photos.map((photo, index) => (
                              <div key={index} className="carousel-slide">
                                <img
                                  src={photo}
                                  alt={`${item.title} - 图片 ${index + 1}`}
                                  className="item-image"
                                  onError={(e) => {
                                    e.target.src = 'https://via.placeholder.com/350x220?text=No+Image';
                                  }}
                                />
                              </div>
                            ))
                          ) : (
                            <div className="carousel-slide">
                              <img
                                src={item.image_url || 'https://via.placeholder.com/350x220?text=No+Image'}
                                alt={item.title}
                                className="item-image"
                                onError={(e) => {
                                  e.target.src = 'https://via.placeholder.com/350x220?text=No+Image';
                                }}
                              />
                            </div>
                          )}
                        </div>
                      </div>
                      {item.detail_data && item.detail_data.photos && Array.isArray(item.detail_data.photos) && item.detail_data.photos.length > 1 && (
                        <div className="carousel-indicators">
                          {item.detail_data.photos.map((_, index) => (
                            <button
                              key={index}
                              className={0 === index ? 'active' : ''}
                              onClick={() => {
                                const track = document.querySelector(`[data-item-id="${item.id || item.item_id}"] .carousel-track`);
                                if (track) {
                                  track.style.transform = `translateX(-${index * 100}%)`;
                                }
                              }}
                            ></button>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="item-content">
                      {item.url ? (
                        <h3 className="item-title">
                          <a href={item.url} target="_blank" rel="noopener noreferrer" className="item-title-link">
                            {item.title}
                          </a>
                        </h3>
                      ) : (
                        <h3 className="item-title">{item.title}</h3>
                      )}
                      <div className="item-price">{item.price}</div>
                      <div className="item-meta">
                        {item.brand && <div className="meta-item">品牌: {item.brand}</div>}
                        {item.detail_data && item.detail_data.item_condition && <div className="meta-item">品质: {item.detail_data.item_condition.name}</div>}
                        {item.detail_data && item.detail_data.shipping_payer && <div className="meta-item">运费: {item.detail_data.shipping_payer.name}</div>}
                      </div>
                      {item.detail_data && (item.detail_data.shipping_method || item.detail_data.shipping_duration || item.detail_data.shipping_from_area) && (
                        <div className="item-shipping-info">
                          {item.detail_data.shipping_method && <div className="shipping-item">配送方式: {item.detail_data.shipping_method.name}</div>}
                          {item.detail_data.shipping_duration && <div className="shipping-item">发货天数: {item.detail_data.shipping_duration.name}</div>}
                          {item.detail_data.shipping_from_area && item.detail_data.shipping_from_area.name && <div className="shipping-item">发货地: {item.detail_data.shipping_from_area.name}</div>}
                        </div>
                      )}
                      {item.description && (
                        <div className="item-description">{item.description}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="item-table-container">
                <table className="item-table">
                  <thead>
                    <tr>
                      <th>商品名称</th>
                      <th>价格</th>
                      <th>品牌</th>
                      <th>品质</th>
                      <th>运费负担</th>
                      <th>配送方式</th>
                      <th>发货天数</th>
                      <th>发货地</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item, index) => (
                      <tr key={item.id || item.item_id} className="table-row" 
                         onDoubleClick={() => handleDoubleClick(item)}>
                        <td>
                          {item.url ? (
                            <a href={item.url} target="_blank" rel="noopener noreferrer" className="table-title-link">
                              {item.title}
                            </a>
                          ) : (
                            item.title
                          )}
                        </td>
                        <td className="table-price">{item.price}</td>
                        <td>{item.brand || '-'}</td>
                        <td>
                          {item.detail_data && item.detail_data.item_condition ? (
                            <span className="condition-badge">
                              {item.detail_data.item_condition.name || '-'}
                            </span>
                          ) : '-'}</td>
                        <td>
                          {item.detail_data && item.detail_data.shipping_payer ? (
                            <span className="shipping-payer">
                              {item.detail_data.shipping_payer.name || '-'}
                            </span>
                          ) : '-'}</td>
                        <td>
                          {item.detail_data && item.detail_data.shipping_method ? (
                            <span className="shipping-method">
                              {item.detail_data.shipping_method.name || '-'}
                            </span>
                          ) : '-'}</td>
                        <td>
                          {item.detail_data && item.detail_data.shipping_duration ? (
                            <span className="shipping-duration">
                              {item.detail_data.shipping_duration.name || '-'}
                            </span>
                          ) : '-'}</td>
                        <td>
                          {item.detail_data && item.detail_data.shipping_from_area && item.detail_data.shipping_from_area.name ? (
                            <span className="shipping-from-area">
                              {item.detail_data.shipping_from_area.name || '-'}
                            </span>
                          ) : '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {totalPages > 1 && (
              <div className="pagination">{renderPagination()}</div>
            )}
          </>
        ) : (
          <div className="empty-state">
            <h2>暂无数据</h2>
            <p>还没有爬取到任何数据，请先启动爬虫。</p>
          </div>
        )}
      </div>

      {/* 弹窗组件 */}
      {showModal && selectedItem && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={closeModal}>
              <i className="fas fa-times"></i>
            </button>
            <div className="item-carousel">
              <div className="carousel-container">
                <div className="carousel-track" style={{ transform: `translateX(-${0 * 100}%)` }}>
                  {selectedItem.detail_data && selectedItem.detail_data.photos && Array.isArray(selectedItem.detail_data.photos) ? (
                    selectedItem.detail_data.photos.map((photo, index) => (
                      <div key={index} className="carousel-slide">
                        <img
                          src={photo}
                          alt={`${selectedItem.title} - 图片 ${index + 1}`}
                          className="item-image"
                          onError={(e) => {
                            e.target.src = 'https://via.placeholder.com/400x300?text=No+Image';
                          }}
                        />
                      </div>
                    ))
                  ) : (
                    <div className="carousel-slide">
                      <img
                        src={selectedItem.image_url || 'https://via.placeholder.com/400x300?text=No+Image'}
                        alt={selectedItem.title}
                        className="item-image"
                        onError={(e) => {
                          e.target.src = 'https://via.placeholder.com/400x300?text=No+Image';
                        }}
                      />
                    </div>
                  )}
                </div>
              </div>
              {selectedItem.detail_data && selectedItem.detail_data.photos && Array.isArray(selectedItem.detail_data.photos) && selectedItem.detail_data.photos.length > 1 && (
                <div className="carousel-indicators">
                  {selectedItem.detail_data.photos.map((_, index) => (
                    <button
                      key={index}
                      className={0 === index ? 'active' : ''}
                      onClick={() => {
                        const track = document.querySelector('.modal-content .carousel-track');
                        if (track) {
                          track.style.transform = `translateX(-${index * 100}%)`;
                        }
                      }}
                    ></button>
                  ))}
                </div>
              )}
            </div>
            <div className="item-content">
              {selectedItem.url ? (
                <h3 className="item-title">
                  <a href={selectedItem.url} target="_blank" rel="noopener noreferrer" className="item-title-link">
                    {selectedItem.title}
                  </a>
                </h3>
              ) : (
                <h3 className="item-title">{selectedItem.title}</h3>
              )}
              <div className="item-price">{selectedItem.price}</div>
              <div className="item-meta">
                {selectedItem.brand && <div className="meta-item">品牌: {selectedItem.brand}</div>}
                {selectedItem.detail_data && selectedItem.detail_data.item_condition && selectedItem.detail_data.item_condition.name && <div className="meta-item">品质: {selectedItem.detail_data.item_condition.name}</div>}
                {selectedItem.detail_data && selectedItem.detail_data.shipping_payer && selectedItem.detail_data.shipping_payer.name && <div className="meta-item">运费: {selectedItem.detail_data.shipping_payer.name}</div>}
              </div>
              {selectedItem.detail_data && (selectedItem.detail_data.shipping_method || selectedItem.detail_data.shipping_duration || selectedItem.detail_data.shipping_from_area) && (
                <div className="item-shipping-info">
                  {selectedItem.detail_data.shipping_method && selectedItem.detail_data.shipping_method.name && <div className="shipping-item">配送方式: {selectedItem.detail_data.shipping_method.name}</div>}
                  {selectedItem.detail_data.shipping_duration && selectedItem.detail_data.shipping_duration.name && <div className="shipping-item">发货天数: {selectedItem.detail_data.shipping_duration.name}</div>}
                  {selectedItem.detail_data.shipping_from_area && selectedItem.detail_data.shipping_from_area.name && <div className="shipping-item">发货地: {selectedItem.detail_data.shipping_from_area.name}</div>}
                </div>
              )}
              {selectedItem.description && (
                <div className="item-description">{selectedItem.description}</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
});

export default DataPage;