#!/bin/bash

# 构建前端
cd frontend
npm install
npm run build
cd ..

# 确保后端依赖已安装
pip install -r requirements.txt
