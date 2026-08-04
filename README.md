# Build Inspiration Library

一个面向建筑、室内与空间创作的视觉灵感图库。项目为纯静态 React + Vite 网站，适合直接部署到 Cloudflare Pages。

## 本地运行

需要 Node.js 22.13 或更高版本。

```bash
npm install
npm run dev
```

## Cloudflare Pages 部署

在 Cloudflare Pages 的构建设置中填写：

- 构建命令：`npm run build`
- 构建输出目录：`dist`
- Node.js 版本：`22.13` 或更高

本项目不需要 Functions、Worker 或 Wrangler 配置。部署后，Cloudflare 直接托管静态文件。

## 本地发布前检查

```bash
npm run build
```

## 每日更新图片

1. 将影刀爬取的新图片直接放入 `public/images/`。
2. 将图片标题、作者、网址等资料追加到根目录的 `图片信息.xlsx`。
3. 双击运行根目录的 `更新图片库.bat`。

该脚本会依次更新网站资料、为未打标的新图片完成 AI 打标，并直接写入 `public/gallery-data.js` 和 `public/image-tags.json`。之后只需将图片与这两个数据文件提交到 GitHub，Cloudflare Pages 会自动更新网站。

## 项目内容

- `app/`：页面与交互组件
- `src/main.tsx`：Vite 浏览器端入口
- `public/images/`：52 张本地图片素材
- `public/gallery-data.js`：原始笔记标题、作者和来源链接
- `public/image-tags.json`：AI 打标数据
