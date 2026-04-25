import { Annotation, AnnotationRelationships } from "../lib/interfaces";
import '../globals.css';

interface Props {
    currentAnnotation: Annotation | null;
    onSelectRelationType: (type: keyof AnnotationRelationships) => void;
    activeRelationType: keyof AnnotationRelationships | null;
    onRemoveRelation: (type: keyof AnnotationRelationships) => void;
    allAnnotations: Annotation[];
}

const RELATIONSHIP_TYPES: Array<{ key: keyof AnnotationRelationships; label: string }> = [
    { key: 'latency', label: 'Latency' },
    { key: 'date', label: 'Date' },
    { key: 'time', label: 'Time' },
    { key: 'frequency', label: 'Frequency' },
    { key: 'temporal_sequence', label: 'Sequence' },
    { key: 'relatives', label: 'Related' }
];

const RelationshipBuilderPanel = (props: Props) => {
    const { currentAnnotation, onSelectRelationType, activeRelationType, onRemoveRelation, allAnnotations } = props;

    if (!currentAnnotation) {
        return (
            <div className="h-full flex items-center justify-center bg-slate-50 text-slate-400 text-sm italic">
                Select an annotation in the narrative to build relationships
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col p-4 bg-white">
            <div className="mb-3 flex items-center justify-between">
                <div className="flex flex-col">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Active Entity</span>
                    <span className="text-sm font-bold text-slate-900 truncate max-w-[200px]">{currentAnnotation.textContext.text}</span>
                </div>
                <div className="px-2 py-1 bg-blue-50 rounded text-[9px] font-bold text-blue-600 uppercase border border-blue-100">
                    {currentAnnotation.label}
                </div>
            </div>

            <div className="grid grid-cols-3 gap-3 overflow-y-auto">
                {RELATIONSHIP_TYPES.map(type => {
                    const targetRef = currentAnnotation.relationships[type.key];
                    let targetText = "Empty";
                    let hasValue = false;

                    if (targetRef) {
                        if (typeof targetRef === 'number') {
                            const target = allAnnotations.find(a => a.id === targetRef);
                            targetText = target ? target.textContext.text : `ID: ${targetRef} (Not Found)`;
                            hasValue = !!target;
                        } else if (typeof targetRef === 'object' && targetRef.text) {
                            targetText = targetRef.text;
                            hasValue = true;
                        }
                    }

                    const isActive = activeRelationType === type.key;

                    return (
                        <div 
                            key={type.key}
                            className={`relative p-3 rounded-xl border transition-all ${
                                isActive 
                                ? 'border-blue-500 bg-blue-50 shadow-sm' 
                                : 'border-slate-100 bg-slate-50/50 hover:bg-slate-50'
                            }`}
                        >
                            <div className="flex items-center justify-between mb-1.5">
                                <span className={`text-[9px] font-bold uppercase tracking-wider ${isActive ? 'text-blue-600' : 'text-slate-400'}`}>
                                    {type.label}
                                </span>
                                {hasValue && (
                                    <button 
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            onRemoveRelation(type.key);
                                        }}
                                        className="text-slate-300 hover:text-red-500 transition-colors"
                                    >
                                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"/></svg>
                                    </button>
                                )}
                            </div>
                            <button
                                onClick={() => onSelectRelationType(type.key)}
                                className={`w-full text-left text-[11px] font-semibold truncate ${
                                    hasValue ? 'text-slate-900' : 'text-slate-400 italic'
                                }`}
                            >
                                {targetText}
                            </button>
                            {isActive && (
                                <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-8 h-1 bg-blue-500 rounded-full"></div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default RelationshipBuilderPanel;
