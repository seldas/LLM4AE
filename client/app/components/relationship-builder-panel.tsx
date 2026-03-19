import { Annotation, AnnotationRelationships } from "../lib/interfaces";
import '../globals.css';
import { capitalizeFirstLetter } from "../lib/util";

interface Props {
    annotations: Annotation[]
    handleSelectCell: (annotation: Annotation, relationshipType: keyof AnnotationRelationships) => void;
    currentAnnotation: Annotation | null;
    currentRelationshipType: keyof AnnotationRelationships | '';
};

interface CellProps {
    value: string;
    annotation: Annotation;
    relationshipType: keyof AnnotationRelationships;
    handleSelectCell: (annotation: Annotation, relationshipType: keyof AnnotationRelationships) => void;
    currentAnnotation: Annotation | null;
    currentRelationshipType: keyof AnnotationRelationships | '';
};

const RelationshipCell = (props: CellProps) => {
  const isSelected =
    props.currentAnnotation === props.annotation &&
    props.currentRelationshipType === props.relationshipType;

  return (
    <td
      className={`relationship-cell ${isSelected ? 'selected' : ''}`}
      onClick={() => props.handleSelectCell(props.annotation, props.relationshipType)}
    >
      {props.value}
    </td>
  );
};

const RelationshipBuilderPanel = (props: Props) => {
    const relationshipOptions: (keyof AnnotationRelationships)[] = ['latency', 'date', 'time', 'temporal_sequence', 'relatives'];
    return (
        <div className="relationship-table-wrapper">
          <table className="relationship-table">
            <thead>
              <tr>
                <th>FID</th>
                <th>Start Position</th>  
                <th>Featured Text</th>
                <th>Annotation Type</th>
                {relationshipOptions.map((a, i) => (
                  <th key={i}>{capitalizeFirstLetter(a).replace("_", " ")}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {props.annotations
                .filter((a) => !["TEMPO", "Status", "Age", "Sex"].includes(a.label))  // TEMPO and Status WILL NOT SHOW IN THE LIST
                .map((a, i) => {
                
                    let rel = a.relationships;
                    let latency = rel.latency?.text || rel.span?.text || "";
                    let temporal_sequence = rel.temporal_sequence?.text || rel.frequency?.text || "";
            
                    return (
                      <tr key={i}>
                        <td>{i}</td>
                        <td>{a.textContext.start}</td>  
                        <td>{a.textContext.text}</td>  
                        <td>{a.label}</td>
                        <RelationshipCell
                          value={latency}
                          annotation={a}
                          relationshipType="latency"
                          handleSelectCell={props.handleSelectCell}
                          currentAnnotation={props.currentAnnotation}
                          currentRelationshipType={props.currentRelationshipType}
                        />
                        <RelationshipCell
                          value={rel.date?.text || ""}
                          annotation={a}
                          relationshipType="date"
                          handleSelectCell={props.handleSelectCell}
                          currentAnnotation={props.currentAnnotation}
                          currentRelationshipType={props.currentRelationshipType}
                        />
                        <RelationshipCell
                          value={rel.time?.text || ""}
                          annotation={a}
                          relationshipType="time"
                          handleSelectCell={props.handleSelectCell}
                          currentAnnotation={props.currentAnnotation}
                          currentRelationshipType={props.currentRelationshipType}
                        />
                        <RelationshipCell
                          value={temporal_sequence}
                          annotation={a}
                          relationshipType="temporal_sequence"
                          handleSelectCell={props.handleSelectCell}
                          currentAnnotation={props.currentAnnotation}
                          currentRelationshipType={props.currentRelationshipType}
                        />
                        <RelationshipCell
                          value={rel.relatives?.text || ""}
                          annotation={a}
                          relationshipType="relatives"
                          handleSelectCell={props.handleSelectCell}
                          currentAnnotation={props.currentAnnotation}
                          currentRelationshipType={props.currentRelationshipType}
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
