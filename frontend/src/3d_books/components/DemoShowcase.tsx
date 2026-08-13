import React, { useState } from 'react';
import { DEMO_BOOKS } from '../data/demoBooks';
import { BookViewer } from './BookViewer';
import type { BookData } from '../types/book';

export const DemoShowcase: React.FC = () => {
  const [booksList, setBooksList] = useState<BookData[]>(DEMO_BOOKS);
  const [selectedBook, setSelectedBook] = useState<BookData>(DEMO_BOOKS[0]);

  // Form state
  const [customTitle, setCustomTitle] = useState('');
  const [customAuthor, setCustomAuthor] = useState('');
  const [customPages, setCustomPages] = useState<number>(300);
  const [customIsRtl, setCustomIsRtl] = useState<boolean>(true);
  const [coverDataUrl, setCoverDataUrl] = useState<string | null>(null);
  const [coverFileName, setCoverFileName] = useState<string | null>(null);
  const [pdfFileName, setPdfFileName] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Reader Modal State
  const [isReaderOpen, setIsReaderOpen] = useState<boolean>(false);
  const [readerPage, setReaderPage] = useState<number>(1);

  const handleCoverSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setCoverFileName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
      const dataUrl = event.target?.result as string;
      if (dataUrl) setCoverDataUrl(dataUrl);
    };
    reader.readAsDataURL(file);
  };

  const handlePdfUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPdfFileName(file.name);
  };

  const handleAddBook = () => {
    if (!coverDataUrl) {
      setStatusMessage('⚠️ يرجى اختيار صورة غلاف الكتاب الـ 3D أولاً.');
      return;
    }

    const titleToUse = customTitle.trim() || (coverFileName ? coverFileName.replace(/\.[^/.]+$/, '') : 'كتاب جديد');
    const newBook: BookData = {
      id: `user-book-${Date.now()}`,
      title: titleToUse,
      author: customAuthor.trim() || 'كتاب عربي',
      pages: customPages || 300,
      coverImage: coverDataUrl,
      isRtl: customIsRtl,
      pdfUrl: pdfFileName || undefined,
      description: `غلاف محمل من المستخدم (${customPages} صفحة ${pdfFileName ? 'مع ملف PDF مرفق' : ''}).`,
    };

    setBooksList((prev) => [newBook, ...prev]);
    setSelectedBook(newBook);
    setCustomTitle('');
    setCustomAuthor('');
    setCoverDataUrl(null);
    setCoverFileName(null);
    setPdfFileName(null);
    setStatusMessage('✨ تم إضافة الكتاب بنجاح وعرضه في الموديل الـ 3D!');
    setTimeout(() => setStatusMessage(null), 4000);
  };

  return (
    <div className="showcase-wrapper">
      <div className="showcase-header">
        <h1>معرض الكتب الـ 3D التفاعلي (3D Book Showcase)</h1>
        <p>عرض مجسمات الكتب ثلاثية الأبعاد بدقة عالية وباتجاه عربي من اليمين. اضغط على زر "فتح وتصفح الكتاب" لقراءة الصفحات.</p>
      </div>

      <div className="showcase-card">
        <h3>📤 إضافة كتاب جديد للمعرض [ بيانات + غلاف 3D + ملف PDF ]</h3>

        <div className="form-grid">
          <div>
            <label>اسم الكتاب</label>
            <input
              type="text"
              placeholder="مثال: كتاب الفيزياء الحديثة"
              value={customTitle}
              onChange={(e) => setCustomTitle(e.target.value)}
            />
          </div>

          <div>
            <label>اسم المؤلف</label>
            <input
              type="text"
              placeholder="مثال: د. أحمد خالد"
              value={customAuthor}
              onChange={(e) => setCustomAuthor(e.target.value)}
            />
          </div>

          <div>
            <label>عدد الصفحات (السُمْك)</label>
            <input
              type="number"
              min={20}
              max={1200}
              value={customPages}
              onChange={(e) => setCustomPages(Number(e.target.value))}
            />
          </div>

          <div>
            <label>اتجاه الكتاب</label>
            <select
              value={customIsRtl ? 'rtl' : 'ltr'}
              onChange={(e) => setCustomIsRtl(e.target.value === 'rtl')}
            >
              <option value="rtl">عربي (الكعب من اليمين)</option>
              <option value="ltr">English (Spine on Left)</option>
            </select>
          </div>
        </div>

        <div className="action-grid">
          <div>
            <label>1. صورة الغلاف 3D</label>
            <label className="btn-upload btn-blue">
              {coverFileName ? `الغلاف: ${coverFileName}` : '🖼️ اختر صورة الغلاف 3D...'}
              <input type="file" accept="image/*" onChange={handleCoverSelect} hidden />
            </label>
          </div>

          <div>
            <label>2. ملف الـ PDF (اختياري)</label>
            <label className={`btn-upload ${pdfFileName ? 'btn-green' : 'btn-slate'}`}>
              {pdfFileName ? `PDF: ${pdfFileName}` : '📄 اختر ملف PDF الكتاب...'}
              <input type="file" accept="application/pdf" onChange={handlePdfUpload} hidden />
            </label>
          </div>

          <div>
            <button onClick={handleAddBook} type="button" className="btn-submit">
              ➕ إضافة الكتاب إلى المعرض
            </button>
          </div>
        </div>

        {statusMessage && (
          <div className={statusMessage.startsWith('⚠️') ? 'msg-error' : 'msg-success'}>
            {statusMessage}
          </div>
        )}
      </div>

      <BookViewer
        book={selectedBook}
        heightPx={360}
        autoRotateDefault={false}
        onOpenBook={() => setIsReaderOpen(true)}
      />

      <div className="books-grid">
        {booksList.map((b) => {
          const isSelected = b.id === selectedBook.id;
          return (
            <div
              key={b.id}
              onClick={() => setSelectedBook(b)}
              className={`book-card ${isSelected ? 'selected' : ''}`}
            >
              <div className="book-card-header">
                <h3>{b.title}</h3>
                <span className="badge">{b.pages} صفحة</span>
              </div>
              <div className="author">المؤلف: {b.author || 'غير محدد'}</div>
              <div className="desc">{b.description}</div>
            </div>
          );
        })}
      </div>

      {isReaderOpen && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <div className="modal-header">
              <div>
                <h2>📖 تصفح كتاب: {selectedBook.title}</h2>
                <p>المؤلف: {selectedBook.author || 'غير محدد'} · {selectedBook.pages} صفحة</p>
              </div>

              <div className="pagination">
                <button
                  onClick={() => setReaderPage((p) => Math.max(1, p - 1))}
                  disabled={readerPage <= 1}
                >
                  ◀ الصفحة السابقة
                </button>
                <span>{readerPage} / {selectedBook.pages}</span>
                <button
                  onClick={() => setReaderPage((p) => Math.min(selectedBook.pages, p + 1))}
                  disabled={readerPage >= selectedBook.pages}
                >
                  الصفحة التالية ▶
                </button>
              </div>

              <button onClick={() => setIsReaderOpen(false)} className="btn-close">
                ✕
              </button>
            </div>

            <div className="modal-body">
              <div className={`paper-view ${selectedBook.isRtl !== false ? 'rtl' : 'ltr'}`}>
                <div>
                  <div className="paper-top">
                    <span>{selectedBook.title}</span>
                    <span>صفحة {readerPage}</span>
                  </div>

                  <h3>{readerPage === 1 ? 'مقدمة الكتاب والتمهيد' : `الفصل ${Math.ceil(readerPage / 5)}: القسم (${readerPage})`}</h3>

                  <p>هذا النص يمثل محتوى قراءة صفحات الكتاب رقم ({readerPage}). يمكنك التنقل وتقليب الصفحات بسهولة من شريط التحكم العلوي.</p>
                  <p>تتضمن هذه الصفحة استعراض الخطوط والمحتويات والنصوص المحررة مع الحفاظ على هوية وتصميم الكتاب الأصلي.</p>
                </div>

                <div className="paper-footer">— {readerPage} —</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
