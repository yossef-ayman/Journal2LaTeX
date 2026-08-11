import React, { useState } from 'react';
import { DEMO_BOOKS } from '../data/demoBooks';
import { BookViewer } from './BookViewer';
import type { BookData } from '../types/book';

export const DemoShowcase: React.FC = () => {
  const [booksList, setBooksList] = useState<BookData[]>(DEMO_BOOKS);
  const [selectedBook, setSelectedBook] = useState<BookData>(DEMO_BOOKS[0]);
  
  // Custom Upload Form state
  const [customTitle, setCustomTitle] = useState('');
  const [customAuthor, setCustomAuthor] = useState('');
  const [customPages, setCustomPages] = useState<number>(300);
  const [customIsRtl, setCustomIsRtl] = useState<boolean>(true); // Default to Arabic RTL (Right side spine)

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const dataUrl = event.target?.result as string;
      if (!dataUrl) return;

      const newBook: BookData = {
        id: `user-book-${Date.now()}`,
        title: customTitle || file.name.replace(/\.[^/.]+$/, ""),
        author: customAuthor || 'كتاب عربي',
        pages: customPages || 300,
        coverImage: dataUrl,
        isRtl: customIsRtl,
        description: `غلاف محمل من المستخدم (${customPages} صفحة - اتجاه ${customIsRtl ? 'عربي من اليمين' : 'إنجليزي'}).`,
      };

      setBooksList((prev) => [newBook, ...prev]);
      setSelectedBook(newBook);
      setCustomTitle('');
      setCustomAuthor('');
    };

    reader.readAsDataURL(file);
  };

  return (
    <div
      style={{
        maxWidth: '1080px',
        margin: '0 auto',
        padding: '24px 16px',
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        color: '#f8fafc',
      }}
    >
      <div style={{ textAlign: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: 800, margin: '0 0 8px 0', letterSpacing: '-0.5px' }}>
          معرض الكتب الـ 3D التفاعلي (3D Book Showcase)
        </h1>
        <p style={{ fontSize: '15px', color: '#94a3b8', margin: 0 }}>
          عرض مجسمات الكتب ثلاثية الأبعاد بدقة عالية وباتجاه عربي من اليمين. اسحب للتعديل وزوم للتكبير.
        </p>
      </div>

      {/* Upload Custom Cover Section */}
      <div
        style={{
          background: 'rgba(30, 41, 59, 0.7)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '16px',
          padding: '16px 20px',
          marginBottom: '24px',
          backdropFilter: 'blur(8px)',
        }}
      >
        <h3 style={{ fontSize: '15px', fontWeight: 700, margin: '0 0 12px 0', color: '#60a5fa' }}>
          📤 رفع غلاف كتاب جديد [ الغلاف الخلفي | الكعب | الغلاف الأمامي ]
        </h3>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '12px', alignItems: 'end' }}>
          <div>
            <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>اسم الكتاب</label>
            <input
              type="text"
              placeholder="مثال: كتاب الفيزياء الحديثة"
              value={customTitle}
              onChange={(e) => setCustomTitle(e.target.value)}
              style={{
                width: '100%',
                background: '#0f172a',
                border: '1px solid rgba(255,255,255,0.15)',
                borderRadius: '8px',
                padding: '8px 12px',
                color: '#fff',
                fontSize: '13px',
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>اسم المؤلف</label>
            <input
              type="text"
              placeholder="مثال: د. أحمد خالد"
              value={customAuthor}
              onChange={(e) => setCustomAuthor(e.target.value)}
              style={{
                width: '100%',
                background: '#0f172a',
                border: '1px solid rgba(255,255,255,0.15)',
                borderRadius: '8px',
                padding: '8px 12px',
                color: '#fff',
                fontSize: '13px',
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>عدد الصفحات (السُمْك)</label>
            <input
              type="number"
              min={20}
              max={1200}
              value={customPages}
              onChange={(e) => setCustomPages(Number(e.target.value))}
              style={{
                width: '100%',
                background: '#0f172a',
                border: '1px solid rgba(255,255,255,0.15)',
                borderRadius: '8px',
                padding: '8px 12px',
                color: '#fff',
                fontSize: '13px',
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>اتجاه الكتاب</label>
            <select
              value={customIsRtl ? 'rtl' : 'ltr'}
              onChange={(e) => setCustomIsRtl(e.target.value === 'rtl')}
              style={{
                width: '100%',
                background: '#0f172a',
                border: '1px solid rgba(255,255,255,0.15)',
                borderRadius: '8px',
                padding: '8px 12px',
                color: '#fff',
                fontSize: '13px',
              }}
            >
              <option value="rtl">عربي (الكعب من اليمين)</option>
              <option value="ltr">English (Spine on Left)</option>
            </select>
          </div>

          <div>
            <label
              style={{
                display: 'block',
                textAlign: 'center',
                background: '#3b82f6',
                color: '#fff',
                padding: '8px 12px',
                borderRadius: '8px',
                fontWeight: 600,
                fontSize: '13px',
                cursor: 'pointer',
                transition: 'background 0.2s',
              }}
            >
              اختر ملف الصورة...
              <input
                type="file"
                accept="image/*"
                onChange={handleFileUpload}
                style={{ display: 'none' }}
              />
            </label>
          </div>
        </div>
      </div>

      {/* Main 3D Book Viewer Stage */}
      <BookViewer book={selectedBook} heightPx={360} autoRotateDefault={false} />

      {/* Book Selection Controls & Info */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '16px',
          marginTop: '28px',
        }}
      >
        {booksList.map((b) => {
          const isSelected = b.id === selectedBook.id;
          return (
            <div
              key={b.id}
              onClick={() => setSelectedBook(b)}
              style={{
                background: isSelected ? 'rgba(59, 130, 246, 0.15)' : '#1e293b',
                border: `2px solid ${isSelected ? '#3b82f6' : 'rgba(255, 255, 255, 0.08)'}`,
                borderRadius: '12px',
                padding: '16px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <h3 style={{ fontSize: '15px', fontWeight: 700, margin: 0, color: isSelected ? '#60a5fa' : '#f8fafc' }}>
                  {b.title}
                </h3>
                <span
                  style={{
                    fontSize: '12px',
                    fontWeight: 600,
                    padding: '3px 7px',
                    borderRadius: '6px',
                    background: 'rgba(255, 255, 255, 0.1)',
                    color: '#e2e8f0',
                  }}
                >
                  {b.pages} صفحة
                </span>
              </div>
              <div style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
                المؤلف: {b.author || 'غير محدد'}
              </div>
              <div style={{ fontSize: '12px', color: '#cbd5e1', lineHeight: '1.4' }}>
                {b.description}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
