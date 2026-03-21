import { Annotation, AnnotationRelationships } from "../lib/interfaces";
import '../globals.css';
import { capitalizeFirstLetter } from "../lib/util";

interface Props {
    annotations: Annotation[]
    handleSelectCell: (annotation: Annotation, relationshipType: keyof AnnotationRelationships) => void;
    currentAnnotation: Annotation | null;
    currentRelationshipType: keyof AnnotationRelationships | '';
    isReadOnly?: boolean;
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

const RelationshipCell = (props: CellProps) => {
    const isSelected = props.currentAnnotation?.textContext.start === props.annotation.textContext.start && 
                       props.currentRelationshipType === props.relationshipType;

    return (
        <td 
            onClick={() => !props.isReadOnly && props.handleSelectCell(props.annotation, props.relationshipType)}
            className={`p-2 border text-center cursor-pointer transition-colors duration-200
                ${isSelected ? 'bg-blue-100 border-blue-500' : 'hover:bg-gray-50'}`}
        >
            {props.value ? (
                <span className="text-xs font-medium text-blue-700 bg-blue-50 px-2 py-1 rounded">
                    {props.value}
                </span>
            ) : (
                <span className="text-xs text-gray-300 italic">Empty</span>
            )}
        </td>
    );
};

const RelationshipBuilderPanel = (props: Props) => {
    return (
        <div className="relationship-builder-panel h-full flex flex-col">
          <div className="mb-4">
            <h2 className="text-sm font-black text-gray-800 uppercase tracking-widest flex items-center gap-2">
              <span className="text-lg">🔗</span> Relationship Linker
            </h2>
            <p className="text-[10px] text-gray-400 font-medium mt-1">
              Select a cell to start linking entities from the narrative
            </p>
          </div>

          <table className="w-full border-collapse bg-white rounded-xl shadow-sm overflow-hidden border border-gray-100">
            <thead className="bg-gray-50">
              <tr>
                <th className="p-2 border text-left text-[10px] font-black text-gray-500 uppercase">Entity</th>
                <th className="p-2 border text-[10px] font-black text-gray-500 uppercase">Latency</th>
                <th className="p-2 border text-[10px] font-black text-gray-500 uppercase">Date</th>
                <th className="p-2 border text-[10px] font-black text-gray-500 uppercase">Time</th>
                <th className="p-2 border text-[10px] font-black text-gray-500 uppercase">Seq</th>
                <th className="p-2 border text-[10px] font-black text-gray-500 uppercase">Rel</th>
              </tr>
            </thead>
            <tbody>
              {props.annotations
                .sort((a,b) => (a.textContext.start||0) - (b.textContext.start||0))
                .map((a, i) => {
                    const rel = a.relationships || {};
                    const temporal_sequence = rel.temporal_sequence?.text || "";
                    
                    return (
                      <tr key={i} className="hover:bg-gray-50/50">
                        <td className="p-2 border">
                          <div className="flex flex-col gap-0.5 max-w-[100px]">
                            <span className="text-[10px] font-bold text-gray-700 truncate" title={a.textContext.text}>{a.textContext.text}</span>
                            <span className="text-[8px] font-black px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 w-fit uppercase">{a.label}</span>
                          </div>
                        </td>
                        <RelationshipCell
                          value={rel.latency?.text || ""}
                          annotation={a}
                          relationshipType="latency"
                          handleSelectCell={props.handleSelectCell}
                          currentAnnotation={props.currentAnnotation}
                          currentRelationshipType={props.currentRelationshipType}
                          isReadOnly={props.isReadOnly}
                        />
                        <RelationshipCell
                          value={rel.date?.text || ""}
                          annotation={a}
                          relationshipType="date"
                          handleSelectCell={props.handleSelectCell}
                          currentAnnotation={props.currentAnnotation}
                          currentRelationshipType={props.currentRelationshipType}
                          isReadOnly={props.isReadOnly}
                        />
                        <RelationshipCell
                          value={rel.time?.text || ""}
                          annotation={a}
                          relationshipType="time"
                          handleSelectCell={props.handleSelectCell}
                          currentAnnotation={props.currentAnnotation}
                          currentRelationshipType={props.currentRelationshipType}
                          isReadOnly={props.isReadOnly}
                        />
                        <RelationshipCell
                          value={temporal_sequence}
                          annotation={a}
                          relationshipType="temporal_sequence"
                          handleSelectCell={props.handleSelectCell}
                          currentAnnotation={props.currentAnnotation}
                          currentRelationshipType={props.currentRelationshipType}
                          isReadOnly={props.isReadOnly}
                        />
                        <RelationshipCell
                          value={rel.relatives?.text || ""}
                          annotation={a}
                          relationshipType="relatives"
                          handleSelectCell={props.handleSelectCell}
                          currentAnnotation={props.currentAnnotation}
                          currentRelationshipType={props.currentRelationshipType}
                          isReadOnly={props.isReadOnly}
                        />
                      </tr>
                    );
              })}
            </tbody>
          </table>
        </div>
    )
};

export default RelationshipBuilderPanel;
