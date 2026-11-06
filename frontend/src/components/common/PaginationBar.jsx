import { Fragment } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import CustomSelect from './CustomSelect';
import { PAGE_SIZE_OPTIONS, normalizePageSizeOptions } from '../../utils/pagination';

/**
 * Reusable PaginationBar component for paginated lists and data tables.
 *
 * @param {Object} props
 * @param {number} props.currentPage Current 1-based page index.
 * @param {number} props.totalPages Total number of calculated pages.
 * @param {number} props.pageSize Selected page size (-1 represents 'All').
 * @param {number} props.totalItems Total item count across all pages.
 * @param {string} [props.itemLabel='questions'] Label for items (e.g. 'questions', 'batches').
 * @param {function(number): void} props.onPageChange Callback when page number is selected.
 * @param {function(number): void} props.onPageSizeChange Callback when page size is changed.
 * @param {Array<number|{value: number, label: string}>} [props.pageSizeOptions] Available page sizes (numbers or option objects; -1 = all).
 * @param {string} [props.className] Additional CSS class names.
 */
export default function PaginationBar({
  currentPage,
  totalPages,
  pageSize,
  totalItems,
  itemLabel = 'questions',
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = PAGE_SIZE_OPTIONS,
  className = ''
}) {
  if (totalItems <= 0) return null;

  const safeCurrentPage = Math.min(Math.max(1, currentPage), totalPages);
  const startIndex = totalItems === 0 ? 0 : (pageSize === -1 ? 1 : (safeCurrentPage - 1) * pageSize + 1);
  const endIndex = pageSize === -1 ? totalItems : Math.min(safeCurrentPage * pageSize, totalItems);

  const pageNumbers = Array.from({ length: totalPages }, (_, i) => i + 1)
    .filter(p => p === 1 || p === totalPages || Math.abs(p - safeCurrentPage) <= 1);

  return (
    <div className={`pagination-bar ${className}`}>
      <div className="pagination-info">
        Showing <strong className="pagination-highlight">{startIndex}-{endIndex}</strong> of{' '}
        <strong className="pagination-highlight">{totalItems}</strong> {itemLabel}
      </div>

      <div className="pagination-right-group">
        <div className="pagination-page-size-selector">
          <span>Show</span>
          <CustomSelect
            value={pageSize}
            onChange={val => {
              onPageSizeChange(Number(val));
              onPageChange(1);
            }}
            options={normalizePageSizeOptions(pageSizeOptions)}
            searchable={false}
            className="pagination-size-select"
          />
          <span>per page</span>
        </div>

        {pageSize !== -1 && totalPages > 1 && (
          <div className="pagination-nav-group">
            <button
              onClick={() => onPageChange(Math.max(1, safeCurrentPage - 1))}
              disabled={safeCurrentPage === 1}
              className="btn-secondary pagination-arrow-btn"
              title="Previous page"
              aria-label="Previous page"
            >
              <ChevronLeft size={13} />
            </button>

            {pageNumbers.map((p, idx, arr) => {
              const prevPage = arr[idx - 1];
              const showEllipsis = prevPage && p - prevPage > 1;
              const isCurrent = p === safeCurrentPage;

              return (
                <Fragment key={p}>
                  {showEllipsis && <span className="pagination-ellipsis">...</span>}
                  <button
                    onClick={() => onPageChange(p)}
                    className={`pagination-page-btn ${isCurrent ? 'pagination-page-btn-active' : ''}`}
                    aria-current={isCurrent ? 'page' : undefined}
                  >
                    {p}
                  </button>
                </Fragment>
              );
            })}

            <button
              onClick={() => onPageChange(Math.min(totalPages, safeCurrentPage + 1))}
              disabled={safeCurrentPage === totalPages}
              className="btn-secondary pagination-arrow-btn"
              title="Next page"
              aria-label="Next page"
            >
              <ChevronRight size={13} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
