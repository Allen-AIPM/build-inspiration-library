"use client";

import { FormEvent, KeyboardEvent, useEffect, useMemo, useState } from "react";
import DepthCarousel from "./components/DepthCarousel";
import SpecularButton from "./components/SpecularButton";
import SplitText from "./components/SplitText";
import TargetCursor from "./components/TargetCursor";

type AiTags = { space_type?: string; design_style?: string; materials?: string[]; color_tone?: string; scene_usage?: string; keywords?: string[] };
type InspirationItem = { id: string; filename: string; image: string; title?: string; author?: string; likes?: number; url?: string; keyword?: string; aiTags?: AiTags };
const tagChoices = ["全部", "中性色", "绿植", "金属", "玻璃", "明亮通透", "庭院/广场", "立面/外观", "现代主义", "清水混凝土", "低饱和", "彩色点缀", "木饰面", "混合风格", "自然主义"];
const starterComments = [{ name: "Rena", time: "刚刚", text: "光影关系很有张力，收藏进材质参考。", initials: "R" }, { name: "周末造房者", time: "2 小时前", text: "很喜欢这种克制的色彩和留白。", initials: "周" }];

function localImage(image: string) { return image.replace(/^image\//, "/images/"); }
function haystack(item: InspirationItem) { return [item.title, item.author, item.keyword, item.aiTags?.space_type, item.aiTags?.design_style, item.aiTags?.color_tone, item.aiTags?.scene_usage, ...(item.aiTags?.materials || []), ...(item.aiTags?.keywords || [])].filter(Boolean).join(" ").toLowerCase(); }
function tagTerms(tag: string) { return ({ "中性色": ["中性", "灰", "低饱和"], "绿植": ["绿植", "植物", "生态"], "金属": ["金属"], "玻璃": ["玻璃"], "明亮通透": ["明亮", "通透", "采光"], "庭院/广场": ["庭院", "广场", "景观"], "立面/外观": ["立面", "外观", "鸟瞰"], "现代主义": ["现代"], "清水混凝土": ["清水混凝土", "混凝土"], "低饱和": ["低饱和"], "彩色点缀": ["彩色", "红色", "色彩"], "木饰面": ["木饰面", "木材", "原木"], "混合风格": ["混合", "融合"], "自然主义": ["自然", "生态"] } as Record<string, string[]>)[tag] || [tag]; }

export default function Home() {
  const [items, setItems] = useState<InspirationItem[]>([]);
  const [selected, setSelected] = useState<InspirationItem | null>(null);
  const [isLightboxOpen, setLightboxOpen] = useState(false);
  const [comments, setComments] = useState(starterComments);
  const [comment, setComment] = useState("");
  const [query, setQuery] = useState("");
  const [activeTag, setActiveTag] = useState("全部");

  useEffect(() => {
    Promise.all([fetch("/gallery-data.js").then((result) => result.text()), fetch("/image-tags.json").then((result) => result.json())]).then(([galleryText, tagData]) => {
      const gallery = JSON.parse(galleryText.replace(/^\s*window\.GALLERY_DATA\s*=\s*/, "").replace(/;\s*$/, ""));
      const tags = new Map<string, AiTags>((tagData.items ?? []).map((tag: AiTags & { image_id: string }) => [tag.image_id, tag]));
      setItems((gallery.items ?? []).map((item: InspirationItem) => ({ ...item, image: localImage(item.image), aiTags: tags.get(item.filename) })));
    }).catch(() => undefined);
  }, []);
  useEffect(() => { const key = (event: globalThis.KeyboardEvent) => { if (event.key === "Escape") isLightboxOpen ? setLightboxOpen(false) : setSelected(null); }; window.addEventListener("keydown", key); return () => window.removeEventListener("keydown", key); }, [isLightboxOpen]);

  const visibleItems = useMemo(() => items.filter((item) => { const content = haystack(item); return (!query || content.includes(query.toLowerCase())) && (activeTag === "全部" || tagTerms(activeTag).some((term) => content.includes(term.toLowerCase()))); }), [items, query, activeTag]);
  const selectedIndex = useMemo(() => selected ? items.findIndex((item) => item.filename === selected.filename) : -1, [items, selected]);
  const carouselItems = items.slice(0, 8).map((item) => ({ image: item.image, alt: item.title }));
  const openDetail = (item: InspirationItem) => { setSelected(item); setComments(starterComments); };
  const submitComment = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const text = comment.trim(); if (!text) return; setComments((current) => [{ name: "灵感策展人", time: "刚刚", text, initials: "灵" }, ...current]); setComment(""); };
  const cardKeyDown = (event: KeyboardEvent<HTMLElement>, item: InspirationItem) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openDetail(item); } };

  return <main><TargetCursor />
    <nav className="topbar" aria-label="主导航"><a data-cursor-target className="brand" href="#top"><span className="brand-sign">BI</span><span>Build Inspiration</span></a><div className="nav-links"><a className="active" href="#gallery">灵感图库</a><a href="#about">关于我们</a></div><a data-cursor-target className="nav-action" href="#gallery">探索作品 <span>↗</span></a></nav>
    <section id="top" className="hero" style={{ backgroundImage: `url(${items[31]?.image || "/images/20260803160531536.jpeg"})` }}><div className="hero-shade" /><div className="hero-content"><p className="eyebrow">ARCHITECTURE / INTERIOR / ATMOSPHERE</p><h1><span className="hero-title-line"><SplitText text="建筑灵感" delay={70} /></span><span className="hero-title-line"><SplitText text="自动被你发现" delay={70} /></span></h1><p className="hero-note">一座持续生长的空间视觉档案，为每一次创作打开新的视角。</p><SpecularButton className="hero-specular" onClick={() => document.getElementById("gallery")?.scrollIntoView({ behavior: "smooth" })}>开始浏览 <b>↓</b></SpecularButton></div><div className="hero-gallery"><p>DEPTH ARCHIVE / 01—08</p><DepthCarousel items={carouselItems} onItemClick={(index) => items[index] && openDetail(items[index])} /></div><div className="hero-counter"><strong>{String(items.length || 52).padStart(2, "0")}</strong><span>CURATED<br />VISUALS</span></div></section>
    <section id="gallery" className="collection"><div className="section-heading"><div><p className="eyebrow dark">CURATED COLLECTION</p><h2>用视觉，拓宽视野</h2></div><p>每一张作品都是一段空间叙事。点击任意图片，沉浸式阅读它的细节。</p></div><div className="gallery-tools"><label className="gallery-search"><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索标题、AI 标签、材料、场景" /></label><div className="tag-chips">{tagChoices.map((tag) => <button data-cursor-target key={tag} className={tag === activeTag ? "is-active" : ""} onClick={() => setActiveTag(tag)}>{tag}</button>)}</div></div><div className="gallery-count">显示 {visibleItems.length} / {items.length || 52} 张图片</div><div className="masonry" aria-label="建筑灵感图片瀑布流">{visibleItems.map((item) => <article className="image-card" role="button" tabIndex={0} data-cursor-target key={item.filename} onClick={() => openDetail(item)} onKeyDown={(event) => cardKeyDown(event, item)}><img src={item.image} alt="建筑与空间灵感作品" loading="lazy" />{item.url && <a className="card-source" href={item.url} target="_blank" rel="noreferrer" aria-label="跳转至原始笔记" onClick={(event) => event.stopPropagation()}>↗</a>}</article>)}</div></section>
    <section id="about" className="about"><p>BUILD INSPIRATION LIBRARY</p><span>为建筑、室内与空间创作收集值得停留的瞬间。</span></section>
    {selected && <section id="detail" className="detail" aria-label="图片详情"><button data-cursor-target className="detail-close" onClick={() => setSelected(null)} aria-label="关闭详情">×</button><div className="detail-inner"><div className="detail-image-wrap"><img src={selected.image} alt={selected.title || "建筑与空间灵感作品大图"} /><SpecularButton className="view-original" onClick={() => setLightboxOpen(true)}>查看原图 <b>↗</b></SpecularButton></div><div className="detail-content"><p className="eyebrow dark">INSPIRATION {String(selectedIndex + 1).padStart(2, "0")}</p><h2>{selected.title || "未命名建筑灵感"}</h2><div className="author-row"><span className="author-avatar">{(selected.author || "灵").slice(0, 1)}</span><div><strong>{selected.author || "灵感策展人"}</strong><small>建筑灵感收藏</small></div><span className="likes">♡ {selected.likes || 0}</span></div><div className="image-meta"><span>{selected.keyword || "建筑灵感"}</span><span>NO. {selected.filename.replace(".jpeg", "").slice(-6)}</span></div><AiTagDetails tags={selected.aiTags} /><div className="comment-area"><div className="comment-heading"><h3>评论 <span>{comments.length}</span></h3><p>留下你的灵感片段</p></div><form onSubmit={submitComment} className="comment-form"><input value={comment} onChange={(event) => setComment(event.target.value)} placeholder="说说你从这张图里看到了什么…" /><SpecularButton type="submit" className="comment-submit">发布</SpecularButton></form><div className="comment-list">{comments.map((entry, index) => <article className="comment" key={`${entry.name}-${index}`}><span className="comment-avatar">{entry.initials}</span><div><div><strong>{entry.name}</strong><time>{entry.time}</time></div><p>{entry.text}</p></div></article>)}</div></div></div></div></section>}
    {selected && isLightboxOpen && <div className="lightbox" role="dialog" aria-modal="true" aria-label="图片原图预览" onClick={() => setLightboxOpen(false)}><button data-cursor-target className="lightbox-close" onClick={() => setLightboxOpen(false)} aria-label="关闭原图预览">×</button><img src={selected.image} alt={selected.title || "建筑与空间灵感原图"} onClick={(event) => event.stopPropagation()} /></div>}
  </main>;
}

function AiTagDetails({ tags }: { tags?: AiTags }) { if (!tags) return <section className="ai-tags"><div className="ai-tags__heading"><span>AI 标注</span><small>尚未生成</small></div><p>这张图片暂未匹配到 AI 标签。</p></section>; const rows = [["空间类型", tags.space_type], ["设计风格", tags.design_style], ["主色调", tags.color_tone], ["适用场景", tags.scene_usage]]; return <section className="ai-tags"><div className="ai-tags__heading"><span>AI 标注</span><small>已生成</small></div><dl>{rows.map(([name, value]) => value && <div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}</dl>{tags.materials?.length ? <div className="tag-group"><b>材质元素</b><span>{tags.materials.map((tag) => <i key={tag}>{tag}</i>)}</span></div> : null}{tags.keywords?.length ? <div className="tag-group"><b>关键词</b><span>{tags.keywords.map((tag) => <i key={tag}>{tag}</i>)}</span></div> : null}</section>; }
