import React, { useState } from 'react';
import { Layout, Typography } from 'antd';
import { DatabaseOutlined, BugOutlined } from '@ant-design/icons';
import CrawlerPage from './components/CrawlerPage';
import DataPage from './components/DataPage';
import './App.css';

const { Header, Content } = Layout;
const { Title } = Typography;

function App() {
  const [currentPage, setCurrentPage] = useState('data');

  return (
    <Layout className="app-container" style={{ minHeight: '100vh', borderRadius: 'var(--border-radius-lg)', overflow: 'hidden' }}>
      <Header className="header" style={{ 
        background: 'rgba(255, 255, 255, 0.95)', 
        padding: '30px 30px', 
        display: 'flex', 
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottom: '2px solid var(--border-color)'
      }}>
        <div className="title-container">
          <Title level={3} style={{ color: 'var(--text-primary)', margin: 0, fontSize: 'clamp(0.9rem, 2vw, 1.5rem)', fontWeight: 700, letterSpacing: '1px', textTransform: 'uppercase' }}>E-COMMERCE DATA COLLECTION SYSTEM</Title>
        </div>
        <nav>
          <button
            className={`nav-btn ${currentPage === 'data' ? 'active' : ''}`}
            onClick={() => setCurrentPage('data')}
            title="数据展示"
          >
            <DatabaseOutlined />
          </button>
          <button
            className={`nav-btn ${currentPage === 'crawler' ? 'active' : ''}`}
            onClick={() => setCurrentPage('crawler')}
            title="爬虫管理"
          >
            <BugOutlined />
          </button>
        </nav>
      </Header>
      
      <Content className="content" style={{ padding: '40px 30px', background: 'var(--bg-primary)' }}>
        {currentPage === 'crawler' && <CrawlerPage />}
        {currentPage === 'data' && <DataPage />}
      </Content>
    </Layout>
  );
}

export default App;
