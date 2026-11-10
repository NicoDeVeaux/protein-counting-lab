import edu.duke.cs.osprey.ematrix.EnergyMatrix;
import java.io.*;
import java.nio.ByteBuffer;
import java.security.MessageDigest;
import java.util.*;
import java.util.zip.*;

public class NativeMatrixCheck {
    static final Set<String> CLASSES = Set.of(
        "edu.duke.cs.osprey.ematrix.EnergyMatrix",
        "edu.duke.cs.osprey.confspace.TupleMatrixDouble",
        "edu.duke.cs.osprey.confspace.AbstractTupleMatrix",
        "java.lang.Double", "java.lang.Number", "[D", "[I"
    );

    static void add(MessageDigest digest, double value) {
        digest.update(ByteBuffer.allocate(8).putDouble(value).array());
    }

    public static void main(String[] args) throws Exception {
        try (ZipFile archive = new ZipFile(args[0])) {
            List<String> names = Collections.list(archive.entries()).stream()
                .map(ZipEntry::getName).filter(name -> name.endsWith(".rigid.dat")).sorted().toList();
            for (String name : names) {
                EnergyMatrix matrix;
                try (ObjectInputStream input = new ObjectInputStream(archive.getInputStream(archive.getEntry(name)))) {
                    input.setObjectInputFilter(info -> {
                        if (info.depth() > 20 || info.references() > 1000 || info.arrayLength() > 10000000) {
                            return ObjectInputFilter.Status.REJECTED;
                        }
                        Class<?> clazz = info.serialClass();
                        return clazz == null || CLASSES.contains(clazz.getName())
                            ? ObjectInputFilter.Status.ALLOWED : ObjectInputFilter.Status.REJECTED;
                    });
                    matrix = (EnergyMatrix)input.readObject();
                    if (input.read() != -1) throw new IOException("Trailing data");
                }
                MessageDigest digest = MessageDigest.getInstance("SHA-256");
                add(digest, matrix.getConstTerm());
                for (int pos=0; pos<matrix.getNumPos(); pos++) {
                    for (int rc=0; rc<matrix.getNumConfAtPos(pos); rc++) add(digest, matrix.getOneBody(pos, rc));
                }
                for (int pos1=0; pos1<matrix.getNumPos(); pos1++) {
                    for (int pos2=0; pos2<pos1; pos2++) {
                        for (int rc1=0; rc1<matrix.getNumConfAtPos(pos1); rc1++) {
                            for (int rc2=0; rc2<matrix.getNumConfAtPos(pos2); rc2++) {
                                add(digest, matrix.getPairwise(pos1, rc1, pos2, rc2));
                            }
                        }
                    }
                }
                String hash = HexFormat.of().formatHex(digest.digest());
                System.out.println(name + "\t" + Arrays.toString(matrix.getNumConfAtPos()) + "\t"
                    + Double.toHexString(matrix.getConstTerm()) + "\t" + hash);
            }
        }
    }
}
