import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { JsonViewer } from "@/components/JsonViewer";

interface RawDataTabProps {
  data: Record<string, unknown>;
}

export function RawDataTab({ data }: RawDataTabProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Raw API Data</CardTitle>
      </CardHeader>
      <CardContent>
        <JsonViewer data={data} maxHeight="600px" />
      </CardContent>
    </Card>
  );
}
