'use client';

import { AnnotationFilterOptions, AnnotationFilters } from '../lib/interfaces';

interface Props {
  annotationFilters: AnnotationFilters;
  handleCheckFilter: (filterOption: AnnotationFilterOptions, checked: boolean) => void;
}

const AnnotationFilter = ({ annotationFilters, handleCheckFilter }: Props) => {
  return (
    <div className="flex flex-col gap-2">
      {Object.entries(annotationFilters).map(([label, isChecked]) => (
        <label key={label} className="flex items-center gap-2 cursor-pointer text-sm">
          <input
            type="checkbox"
            value={label}
            checked={isChecked}
            onChange={(e) =>
              handleCheckFilter(label as AnnotationFilterOptions, e.target.checked)
            }
            className="accent-blue-600"
          />
          {label}
        </label>
      ))}
    </div>
  );
};

export default AnnotationFilter;
