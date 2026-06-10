import { Annotation, AnnotationRelationships } from "../lib/interfaces";
import '../globals.css';
import { capitalizeFirstLetter } from "../lib/util";

interface Props {
    annotations: Annotation[]
    handleSelectCell: (annotation: Annotation, relationshipType: keyof AnnotationRelationships) => void;
    currentAnnotation: Annotation | null;
    currentRelationshipType: keyof AnnotationRelationships | '';
    isReadOnly?: boolean;
    temporalTerms: Annotation[];
    currentAnnotationIsPrimary: boolean;
    selectedTermContext: { text: string; start: number; end: number } | null;
};

interface CellProps {
    value: string;
    annotation: Annotation;
    relationshipType: keyof AnnotationRelationships;
    handleSelectCell: (annotation: Annotation, relationshipType: keyof AnnotationRelationships) => void;
    currentAnnotation: Annotation | null;
    currentRelationshipType: keyof AnnotationRelationships | '';
    isReadOnly?: boolean;
};

const RELATIONSHIP_TYPES: Array<{ key: keyof AnnotationRelationships; label: string }> = [
    { key: 'latency', label: 'Latency' },
    { key: 'date', label: 'Date' },
    { key: 'time', label: 'Time' },
    { key: 'temporal_sequence', label: 'Sequence' },
    { key: 'relatives', label: 'Related' }
];

const RelationshipBuilderPanel = (props: Props) => {
    const annotations = props.annotations
        .sort((a,b) => (a.textContext.start||0) - (b.textContext.start||0));
    const currentAnnotation = props.currentAnnotation;
    return (
        <div className="relationship-builder-panel h-full flex flex-col gap-4">
          <div>
            <p className="text-[11px] text-slate-500 font-semibold bg-slate-50 border border-slate-100 p-3 rounded-lg leading-relaxed">
              <span className="text-blue-600 font-bold">Step 1:</span> Select the entity you want to link below.<br/>
              <span className="text-blue-600 font-bold">Step 2:</span> Highlight the corresponding term in the narrative above to assign it to the active slot.
            </p>
          </div>

          <div className="space-y-3 overflow-y-auto pr-1 flex-1">
            {annotations
              .filter(annotation => !currentAnnotation || annotation.textContext.start === currentAnnotation.textContext.start)
              .map((annotation, idx) => {
                const isActiveEntity = props.currentAnnotation?.textContext.start === annotation.textContext.start;
                const rel = annotation.relationships || {};
                return (
                    <div key={idx} className={`p-3 rounded-2xl border ${isActiveEntity ? 'border-blue-300 bg-blue-50' : 'border-slate-100 bg-white'} shadow-[0_8px_24px_rgba(15,23,42,0.05)]`}>
                        <div className="flex items-center justify-between mb-2 gap-2">
                            <div className="flex flex-col">
                                <span className="text-[11px] font-semibold text-slate-800 truncate">{annotation.textContext.text}</span>
                                <span className="text-[8px] font-black uppercase tracking-[0.3em] text-slate-400">{annotation.label}</span>
                            </div>
                            <span className="text-[9px] font-bold text-blue-500">{isActiveEntity ? 'Active' : 'Inactive'}</span>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                            {RELATIONSHIP_TYPES.map(type => {
                                const value = rel[type.key]?.text || '';
                                const isSelected = isActiveEntity && props.currentRelationshipType === type.key;
                                return (
                                    <button
                                        key={type.key}
                                        onClick={() => !props.isReadOnly && props.handleSelectCell(annotation, type.key)}
                                        className={`text-left text-[10px] font-semibold px-3 py-2 rounded-lg border transition-all ${isSelected ? 'border-blue-500 bg-blue-100 text-blue-800 shadow-inner' : 'border-slate-200 bg-slate-50 hover:border-slate-300'}`}
                                    >
                                        <span className="block text-[9px] uppercase tracking-[0.4em] text-slate-400">{type.label}</span>
                                        <span className={`${value ? 'text-slate-800' : 'text-slate-400 italic'}`}>{value || 'Empty'}</span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                );
            })}
            {annotations.length === 0 && (
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-[11px] text-slate-500 text-center">
                    No entities available for linking.
                </div>
            )}
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-slate-400 mb-2">Temporal candidates</p>
                <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto pr-1">
                    {props.temporalTerms.length > 0 ? props.temporalTerms.map((term, i) => (
                        <span
                            key={`${term.textContext.start || 0}-${i}`}
                            className="text-[10px] font-semibold px-3 py-1 rounded-full border border-slate-200 bg-white text-slate-500"
                            title={term.textContext.text}
                        >
                            {term.textContext.text.length > 20 ? `${term.textContext.text.slice(0, 20)}...` : term.textContext.text}
                        </span>
                    )) : (
                        <span className="text-[10px] italic text-slate-400">No temporal terms available</span>
                    )}
                </div>
                {!props.currentAnnotationIsPrimary && (
                    <p className="text-[9px] italic text-slate-500 mt-2">Select a primary AE/Drug entity above to activate linking.</p>
                )}
            </div>
          </div>
        </div>
    )
};

export default RelationshipBuilderPanel;
