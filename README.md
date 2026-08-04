# Build Inspiration Library

一个面向建筑、室内与空间创作的视觉灵感图库。项目使用 React + Vite（vinext）构建，包含瀑布流图库、AI 标签检索、图片详情、大图预览与本地评论交互。

## 本地运行

需要 Node.js 22.13 或更高版本。

```bash
npm install
npm run dev
```

在浏览器打开终端显示的本地地址即可预览。

## 发布前检查

```bash
npm run build
```

## 上传到 GitHub

将整个项目文件夹上传到新的 GitHub 仓库即可。`.gitignore` 已排除依赖目录、构建文件、日志和本地配置；图片素材与 AI 标签数据位于 `public/`，会一并提交。

## 项目内容

- `app/`：页面与交互组件
- `public/images/`：52 张本地图片素材
- `public/gallery-data.js`：原始笔记标题、作者和来源链接
- `public/image-tags.json`：AI 打标数据
